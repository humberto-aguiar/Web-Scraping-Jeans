#!usr/bin/bash

# specifying date
dt=$(date '+%Y-%m-%d--%H:%M:%S')

# paths
#which papermill to use (venv)
path_papermill="/home/ubuntu/.pyenv/versions/3.8.0/envs/web_scraping/bin/papermill"

# lastest file to run
file_to_execute="selenium_debugger.ipynb"

# printing msg
echo -e "Starting Web Scraping\n"

# paths
path_file="/home/ubuntu/project/Web-Scraping-Jeans/src/$file_to_execute"
path_log="/home/ubuntu/project/Web-Scraping-Jeans/src/logs/$file_to_execute-date:$dt.ipynb"

# runing papermill deploy file on log path
$path_papermill $path_file $path_log