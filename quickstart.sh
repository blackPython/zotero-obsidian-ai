#!/bin/bash

# Zotero-Obsidian AI Quick Start Script

echo "🚀 Zotero-Obsidian AI Research Assistant Quick Start"
echo "===================================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi
echo "✅ Python found: $(python3 --version)"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 16 or higher."
    exit 1
fi
echo "✅ Node.js found: $(node --version)"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "⚠️  AWS CLI not found. Make sure AWS credentials are configured."
fi

echo ""
echo "📝 Configuration Setup"
echo "====================="

# Get Zotero credentials
if [ ! -f backend/.env ]; then
    echo ""
    echo "Please provide your Zotero API credentials:"
    echo "(Get them from https://www.zotero.org/settings/keys)"
    echo ""

    read -p "Zotero API Key: " ZOTERO_API_KEY
    read -p "Zotero Library ID (your userID): " ZOTERO_LIBRARY_ID

    echo ""
    echo "AWS Configuration:"
    read -p "AWS Region (default: us-east-1): " AWS_REGION
    AWS_REGION=${AWS_REGION:-us-east-1}

    # Create .env file
    cat > backend/.env << EOF
# Zotero Configuration
ZOTERO_API_KEY=$ZOTERO_API_KEY
ZOTERO_LIBRARY_ID=$ZOTERO_LIBRARY_ID
ZOTERO_LIBRARY_TYPE=user

# AWS Configuration
AWS_REGION=$AWS_REGION
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Processing Configuration
MAX_TOKENS=4096
CHUNK_SIZE=3000
CHUNK_OVERLAP=200
SYNC_INTERVAL=300
SYNC_DAYS_BACK=30
EOF

    echo "✅ Configuration saved to backend/.env"
else
    echo "✅ Configuration file already exists"
fi

echo ""
echo "🔧 Setting up Backend"
echo "===================="

cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "✅ Backend setup complete"

cd ..

echo ""
echo "🎨 Building Obsidian Plugin"
echo "=========================="

cd obsidian-plugin

# Install dependencies
echo "Installing Node dependencies..."
npm install --silent

# Build plugin
echo "Building plugin..."
npm run build

echo "✅ Plugin built successfully"

cd ..

echo ""
echo "📦 Installation Instructions"
echo "==========================="
echo ""
echo "1. Start the backend service:"
echo "   cd backend && source venv/bin/activate && python main.py"
echo ""
echo "2. Install the Obsidian plugin:"
echo "   - Open Obsidian Settings → Community plugins"
echo "   - Turn off 'Restricted mode'"
echo "   - Click the folder icon to open plugins folder"
echo "   - Copy these files to .obsidian/plugins/zotero-ai-assistant/:"
echo "     - obsidian-plugin/main.js"
echo "     - obsidian-plugin/manifest.json"
echo "   - Reload Obsidian (Ctrl/Cmd + R)"
echo "   - Enable 'Zotero AI Research Assistant' plugin"
echo ""
echo "3. Configure the plugin in Obsidian settings with:"
echo "   - Backend URL: http://localhost:8000"
echo "   - Your Zotero credentials"
echo ""
echo "📚 For detailed setup instructions, see SETUP.md"
echo ""
echo "✨ Quick start complete! Follow the instructions above to begin."