#!/bin/bash

# Read .env file and set each variable in Heroku
while IFS='=' read -r key value
do
    # Skip empty lines and comments
    if [[ -n "$key" && ! "$key" =~ ^# ]]; then
        # Remove any quotes from the value
        value=$(echo $value | tr -d '"')
        # Remove any leading/trailing whitespace
        key=$(echo $key | xargs)
        value=$(echo $value | xargs)
        
        echo "Setting $key"
        heroku config:set "$key=$value"
    fi
done < .env

echo "Done setting config vars!"