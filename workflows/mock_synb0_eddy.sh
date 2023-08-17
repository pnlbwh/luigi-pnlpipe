#!/bin/bash
echo "Processing for LSB_JOBINDEX=$LSB_JOBINDEX"

# add code to make sure the correct cuda visible device is used, there are 4 gpus so % job index by 4
export CUDA_VISIBLE_DEVICES=$((LSB_JOBINDEX % 4))

# print out the device id
echo "CUDA_VISIBLE_DEVICES=$CUDA_VISIBLE_DEVICES"

# sleep for a random amount of time between 10 and 30 seconds
sleep $((RANDOM % 20 + 10))


echo "Completed for LSB_JOBINDEX=$LSB_JOBINDEX"

