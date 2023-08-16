#!/bin/bash

CASELIST_PATH="/path/to/your/caselist.txt" # specify your caselist path here
OUTPUT_DIR="/data/pnl/Collaborators/CMA/mtsintou/Emotion/Output/"
SCRIPT_PATH="/rfanfs/pnl-zorro/software/pnlpipe3/luigi-pnlpipe/workflows/synb0_eddy.sh"
MAX_PARALLEL_JOBS=4

# Count the total number of cases
TOTAL_CASES=$(wc -l < "$CASELIST_PATH")

# Keep track of our jobs
declare -a my_jobs

# Function to get the current number of your specific background jobs
get_my_job_count() {
    local count=0
    for pid in "${my_jobs[@]}"; do
        # Check if the PID exists using ps
        if ps -p $pid > /dev/null; then
            count=$((count+1))
        fi
    done
    echo $count
}

for (( i=1; i<=$TOTAL_CASES; i++ )); do
    while [ $(get_my_job_count) -ge $MAX_PARALLEL_JOBS ]; do
        # Wait for a short duration before checking again
        sleep 10
    done

    # Set and export the LSB_JOBINDEX
    export LSB_JOBINDEX=$i
    echo "Starting job for LSB_JOBINDEX=$LSB_JOBINDEX"

    "$SCRIPT_PATH" > "${OUTPUT_DIR}/${LSB_JOBINDEX}.txt" 2>&1 &

    # Store the PID of the job we just started
    my_jobs+=("$!")
done

# Wait for all background jobs to finish
wait

echo "All jobs completed!"
