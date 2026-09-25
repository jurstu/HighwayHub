#!/bin/bash

ENV_NAME="HighwayHubEnv"
REQUIREMENTS_FILE="requirements.txt"

content=$(<./venvPath)
eval "path=$content"
echo $path
PROJECT_PATH=$path
ENV_PATH="$PROJECT_PATH/$ENV_NAME"

# Create virtual environment
echo "🔧 Creating virtual environment at $ENV_PATH ..."
python3 -m venv "$ENV_PATH"

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment."
    exit 1
fi

# Install requirements if file exists
REQ_FILE="./$REQUIREMENTS_FILE"
if [ -f "$REQ_FILE" ]; then
    echo "📦 Installing dependencies from $REQ_FILE ..."
    source "$ENV_PATH/bin/activate"
    pip install -r "$REQ_FILE"
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies."
        deactivate
        exit 1
    fi
    deactivate
else
    echo "⚠️  No requirements.txt found at $REQ_FILE — skipping install."
fi

# Activation instructions
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source \"$ENV_PATH/bin/activate\""