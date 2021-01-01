#!/bin/bash

pip3 install --upgrade -r requirements.txt
pip install --upgrade --no-deps --force-reinstall git+https://github.com/shellcodesniper/aws_logging_handlers.git
