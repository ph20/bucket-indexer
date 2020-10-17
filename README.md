# bucket-indexer
Utils for generating html index of files on cloud buckets


# Deploying development environment based on conda
1. Install conda https://docs.conda.io/projects/conda/en/latest/user-guide/install/
   See details about installation lightweight version named miniconda
   https://docs.conda.io/en/latest/miniconda.html

2. Deploy and activate runtime envirenment

`conda env create -f environment.yml`

`conda activate bucket-indexer`
# Usage
1. Installation:

`pip3 install git+https://github.com/ph20/bucket-indexer.git`

2. Generating index files on google storage:

`gsindexer gs://bucket-name`
   
Based on templates and ideas from [Index Generator](https://github.com/index-generator-project/index-generator)
