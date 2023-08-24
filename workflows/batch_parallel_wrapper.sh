#!/bin/bash

# Define the path for the list of cases.
CASELIST_PATH="/data/pnl/Collaborators/EDCRP/1110/1110_ses-002_T1_nii/caselist_all_dwi_t1.txt"

# Define the directory where the output logs for each job will be saved.
OUTPUT_DIR="/data/pnl/Collaborators/EDCRP/1110/1110_ses-002_T1_nii/Output"

# Define the path to the script that will be run for each case.
SCRIPT_PATH="/data/pnl/Collaborators/EDCRP/1110/1110_ses-002_T1_nii/synb0_eddy.sh"

# Define the maximum number of parallel jobs you want to run at a time.
MAX_PARALLEL_JOBS=$(nvidia-smi -L | wc -l)

# set the start time for time profiling
START_TIME=$(date +%s)


# Count the total number of cases.
# 'wc -l' counts the number of lines in the file.
TOTAL_CASES=$(wc -l < "$CASELIST_PATH")

# This function is responsible for running a "batch" of jobs.
run_batch() {
    # The start and end indices of the batch are passed as arguments.
    local start=$1
    local end=$2

    # Declare an array to keep track of the background job PIDs within this batch.
    declare -a local_jobs

    # Iterate over each index in the batch range.
    for (( j=$start; j<=$end; j++ ))
    do
        # Set the current index as LSB_JOBINDEX, which may be used by the SCRIPT_PATH.
        export LSB_JOBINDEX=$j
        echo "Starting job for LSB_JOBINDEX=$LSB_JOBINDEX"

        # Run the script in the background (& at the end).
        # Any output (both stdout and stderr) will be redirected to a file named after the current index.
        $SCRIPT_PATH $CASELIST_PATH > "${OUTPUT_DIR}/${LSB_JOBINDEX}.txt" 2>&1 &

        # Save the PID (process ID) of the background job we just started in our array.
        local_jobs+=("$!")
    done

    # This loop waits for each job in the current batch to complete.
    # It ensures we don't start a new batch until the current batch is done.
    for job in "${local_jobs[@]}"
    do
        wait $job
    done
}

# This loop schedules the jobs in batches.
for (( i=1; i<=$TOTAL_CASES; i+=MAX_PARALLEL_JOBS ))
do
    # Calculate the last index of the current batch.
    end=$((i + MAX_PARALLEL_JOBS - 1))

    # If the calculated end exceeds the total number of cases, adjust it.
    if [[ $end -gt $TOTAL_CASES ]]
    then
        end=$TOTAL_CASES
    fi

    # Run the current batch.
    run_batch $i $end
done

# Calculate the elapsed time.
ELAPSED_TIME=$(($(date +%s) - $START_TIME))

# Once all batches have been processed, print a completion message.
echo "All jobs completed!"
# Print the elapsed time.
echo "Elapsed time: $(($ELAPSED_TIME/60)) min $(($ELAPSED_TIME%60)) sec"
