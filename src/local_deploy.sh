#!usr/bin/bash

# specifying date
dt=$(date '+%Y-%m-%d--%H:%M:%S')

# paths
#which papermill to use (venv)
path_papermill="/home/humberto/.pyenv/versions/3.8.0/envs/web_scraping/bin/papermill"

# lastest file to run
file_to_execute="hm-web-scraping-v03.ipynb"

# printing msg
echo -e "Starting Web Scraping\n"

# paths
path_file="/home/humberto/DS/hm/src/$file_to_execute"
path_log="/home/humberto/DS/hm/src/logs/$file_to_execute-date:$dt.ipynb"

# runing papermill deploy file on log path
$path_papermill $path_file $path_log