#!/usr/bin/env nextflow
/*
========================================================================================
    PACT FIO Pipeline
========================================================================================
*/
nextflow.enable.dsl = 2
PIPELINE_NAME = 'FIO'
VERSION = 0.1
/*
========================================================================================
    VALIDATE INPUTS
========================================================================================
*/

// Check input path parameters to see if they exist
checkPathParamList = [
    params.input
]
for (param in checkPathParamList) { if (param) { file(param, checkIfExists: true) } }

// Check mandatory parameters
if (params.input) { ch_input = file(params.input) } else { exit 1, 'Input samplesheet not specified!' }
params.email = [:]

// Conda enviroment location
params.conda_basedir = file(params.condaprefix).getParent() 

// Header log info
log.info "========================================="
log.info "FIO v${VERSION}"
log.info "Nextflow Version:	$workflow.nextflow.version"
log.info "Command Line:		$workflow.commandLine"
log.info "========================================="

/*
========================================================================================
    NAMED WORKFLOW FOR PIPELINE
========================================================================================
*/
include { PROCESS_EXPRS } from './process_exprs/workflow/process_exprs'
include { TME           } from './tme/workflow/tme'

Channel.from(ch_input)
    .splitCsv(sep: '\t', header: true)
    .set { ch_input }

workflow FIO {
    PROCESS_EXPRS (
        ch_input
    )
    
    TME (
        PROCESS_EXPRS.out.pe_input,
        PROCESS_EXPRS.out.emats
    )
}

workflow.onComplete {
    log.info("=======================================")
    status="${ workflow.success ? 'OK' : 'FAILED' }"
    message="Pipeline completed at: ${workflow.complete}\nExecution status: ${status}\nWorkdir: ${workflow.workDir}\nPublish dir: ${params.outdir}"
    log.info(message)

    // Email 
    if ( params.email ) {
        log.info("Emailing ${params.email}")
        subject="FIO ${status}"
        ['aws', 'sns', 'publish', '--topic-arn', 'arn:aws:sns:us-west-2:757652839166:scrnaseq-nextflow-pipeline', '--subject', subject, '--message', message, '--region', 'us-west-2'].execute()
    }
}

/*
========================================================================================
    RUN ALL WORKFLOWS
========================================================================================
*/

//
// WORKFLOW: Execute a single named workflow for the pipeline
// See: https://github.com/nf-core/rnaseq/issues/619
//
workflow {
    FIO ()
}

/*
========================================================================================
    THE END
========================================================================================
*/
