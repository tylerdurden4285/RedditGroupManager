#!/bin/sh
# Install node dependencies for tests if not already installed
REPO_ROOT="$(dirname "$0")/.."
cd "$REPO_ROOT" || exit 1
if [ ! -d node_modules ]; then
    npm install jsdom dompurify marked
fi
