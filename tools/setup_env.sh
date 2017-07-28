#!/bin/bash


# Gotta be somewhere in the tree to run this
git rev-parse || exit

cd $(git rev-parse --show-toplevel)

# Create dirs for customer data, scratch area
mkdir -p \
   data/my_cloud/model \
   data/my_cloud/config \
   data/scratch \
   log

cd data
git clone https://git.suse.provo.cloud/hp/hlm-input-model -b hp/prerelease/ocata

git clone https://git.suse.provo.cloud/hp/hlm-ansible -b hp/prerelease/ocata
