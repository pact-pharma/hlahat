""" FIO Pipeline """
import pandas as pd
import argparse
import os
import subprocess as sb
import yaml
import logging
from importlib.resources import files
import nextflow 
from process_exprs import data as pe_data
from tme import R as tme_R
from commonLib.lib.fileio import check_paths_exist, package_file_path, find_file
from commonLib.lib.search import locate
from commonLib.lib.munge import get_timestamp

def parse_args(args=None):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter, description=__doc__)
    parser.add_argument('pipeline', type=str, default=package_file_path(nextflow, 'main.nf'),
        choices=['all', 'tme', 'process_exprs', 'hlacn'], help='Pipeline to run')
    parser.add_argument('input_dir', help='EPIC pipeline input path')
    parser.add_argument('-m' ,'--manifest', help='EPIC pipeline sample manifest')
    parser.add_argument('-o', '--output_dir', default='output', help='Output directory')
    parser.add_argument('-tsv', '--tsv', help='Nextflow input tsv to write')
    parser.add_argument('-p', '--params', help='Nextflow parameters file')
    parser.add_argument('-t', '--tracing', action='store_true', help='Enable Nextflow report file generation')
    parser.add_argument('-bg', '--background', action='store_true', help='Run in background')
    parser.add_argument('-n', '--dryrun', action='store_true', help='Dry run')
    parser.add_argument('--resume', action='store_true', help='Nextflow resume last job')
    parser.add_argument('--email', help='Email address for pipeline messaging')
    parser.add_argument('--extra', help='Comma separated list of extra args')
    parser.add_argument('--genome_fasta', help='Genome FASTA file')
    
    return parser.parse_args(args)

def nextflow_cmd(script:str, tsv:str, params:str, tracing:bool, background:bool, resume:bool, extra:bool, output_dir:str):
    cmd = [
        'nextflow', 'run', script, 
        '--input', tsv,
    ]
    if params:
        cmd.extend([ '-params-file', params])
    if tracing:
        cmd.extend([
            '-with-report', f'{output_dir}/report.html',
            '-with-timeline', f'{output_dir}/timeline.html',
            '-with-dag', f'{output_dir}/dag.html',
        ])
    if background:
        cmd.extend(['-bg'])
    if resume:
        cmd.extend(['-resume'])
    if extra:
        args = extra.strip("\"'").split(',')
        cmd.extend(args)
    return cmd

def fio_config(input_folder:str):
    # Manifest
    fn = f'manifest*.yml'
    manifest_f = find_file(input_folder, fn)
 
    config = {
        'manifest_f': manifest_f
    }
    return config

def subset_args(args, keep:list):
    return(argparse.Namespace(**{k: v for k, v in args._get_kwargs() if k in keep}))

def main():
    args = parse_args()
#    args = parse_args([
#        'all',
##        'tme',
##        'process_exprs',
#        '/tmp/nomf',
#        #'./test_data/PACT056_T_196454',
#        '--tsv', '/tmp/input.tsv',
#        '--tracing',
#        '--resume',
#        '-bg',
#        '--resume',
#        '-n',
#        #'--manifest', './test_data/manifest_for_testing.yml',
#    ])
    timestamp = get_timestamp().split('+')[0]
    # Check inputs exist
    exists = check_paths_exist([args.input_dir])
    for k,v in exists.items():
        if not v:
            raise FileNotFoundError(k)

    ## Write nextflow input tsv
    # Manifest
    config = fio_config(args.input_dir)
    if not args.manifest:
        args.manifest = config['manifest_f']
    mf_d = yaml.safe_load(open(args.manifest))
    sample = mf_d['pipeline']['pact_id']

    row = {
        'sample': mf_d['pipeline']['pact_id'],
        'manifest': os.path.abspath(args.manifest),
        'input_folder': os.path.abspath(args.input_dir)
    }
    df = pd.DataFrame([row])
    if not args.tsv:
        args.tsv = f'input_{timestamp}.tsv'
    df.to_csv(args.tsv, sep='\t', index=False)

    ## Nextflow command
    keep = ['script', 'tsv', 'params', 'tracing', 'background', 'resume', 'extra', 'output_dir']
    if not args.params:
        args.params = package_file_path(nextflow, 'pipeline.yml')
    if args.pipeline == 'all':
        args.script = package_file_path(nextflow, 'main.nf')
        args_nf = subset_args(args, keep)
        cmd = nextflow_cmd(**vars(args_nf))
        # process_exprs
        cmd.extend(['--tcga_gtex_map', package_file_path(pe_data, 'tcga_gtex.tsv')])
        # tme
        cmd.extend(['--rmd', package_file_path(tme_R, '')])
    if args.pipeline == 'tme':
        args.script = package_file_path(nextflow, 'tme/main.nf')
        args_nf = subset_args(args, keep)
        cmd = nextflow_cmd(**vars(args_nf))
        cmd.extend(['--rmd', package_file_path(tme_R, '')])
    if args.pipeline == 'process_exprs':
        args.script = package_file_path(nextflow, 'process_exprs/main.nf')
        args_nf = subset_args(args, keep)
        cmd = nextflow_cmd(**vars(args_nf))
        cmd.extend(['--tcga_gtex_map', package_file_path(pe_data, 'tcga_gtex.tsv')])
    if args.pipeline == 'hlacn':
        args.script = package_file_path(nextflow, 'pactescape/hlacn/main.nf')
        args_nf = subset_args(args, keep)
        cmd = nextflow_cmd(**vars(args_nf))
        cmd.extend(['--genome_fasta', args.genome_fasta])
    if args.email:
        cmd.extend(['--email', args.email])

    if args.dryrun:
        print(' '.join(cmd))
    else:
        job = sb.run(cmd)

if __name__ == "__main__":
    main()
