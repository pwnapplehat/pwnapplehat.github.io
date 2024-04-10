#!/bin/bash

# Loop through each .deb file in the current directory
for file in *.deb; do
    # Ensure that $file is a file 
    if [ -f "$file" ]; then
        echo "Processing $file..."
        # MD5
        md5=$(md5 -q "$file")
        echo "MD5: $md5"
        
        # SHA1
        sha1=$(shasum -a 1 "$file" | awk '{print $1}')
        echo "SHA1: $sha1"
        
        # SHA256
        sha256=$(shasum -a 256 "$file" | awk '{print $1}')
        echo "SHA256: $sha256"
        
        # File size
        size=$(stat -f%z "$file")
        echo "Size: $size bytes"
        
        echo "--------------------------------"
    fi
done
