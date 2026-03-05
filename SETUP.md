# Setup Guide for Zotero-Obsidian AI Research Assistant

## Prerequisites

- Python 3.9 or higher
- Node.js 16 or higher
- AWS Account with Bedrock access
- Zotero account with API access
- Obsidian installed

## Step 1: Configure AWS Bedrock

1. **Set up an AWS CLI profile** (if you don't have one already):
   ```bash
   aws configure --profile your-profile-name
   # Enter your AWS credentials when prompted
   ```

2. **Request model access**:
   - Go to AWS Bedrock console
   - Navigate to "Model access"
   - Request access to Claude models
   - Wait for approval (usually instant)

3. **Note your profile name and region** (e.g., profile `my-research`, region `us-east-1`)

## Step 2: Get Zotero API Credentials

1. Go to https://www.zotero.org/settings/keys
2. Click "Create new private key"
3. Give it a name (e.g., "Obsidian AI Integration")
4. Grant permissions:
   - ✅ Allow library access
   - ✅ Allow notes access
   - ✅ Allow file access
5. Copy the generated API key
6. Find your Library ID:
   - Go to https://www.zotero.org/settings/keys
   - Your numeric **userID** is shown near the top of the page (e.g., `12345678`)
   - This userID is what you enter as the "Library ID" in the plugin settings

## Step 3: Setup Backend Service

### Install Python dependencies

```bash
cd ~/zotero-obsidian-ai/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configure environment

Create `.env` file in the backend directory:

```bash
cat > ~/zotero-obsidian-ai/backend/.env << 'EOF'
# Zotero Configuration
ZOTERO_API_KEY=your_zotero_api_key_here
ZOTERO_LIBRARY_ID=your_library_id_here
ZOTERO_LIBRARY_TYPE=user

# AWS Configuration
AWS_PROFILE=your_aws_profile_name
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Processing Configuration
MAX_TOKENS=4096
CHUNK_SIZE=3000
CHUNK_OVERLAP=200
SYNC_INTERVAL=300
SYNC_DAYS_BACK=30
EOF
```

Replace the placeholder values with your actual credentials.

### Start the backend service

```bash
cd ~/zotero-obsidian-ai/backend
source venv/bin/activate
python main.py
```

The service will start on http://localhost:8000

## Step 4: Build and Install Obsidian Plugin

### Build the plugin

```bash
cd ~/zotero-obsidian-ai/obsidian-plugin
npm install
npm run build
```

### Install in Obsidian

1. Open your Obsidian vault
2. Go to Settings → Community plugins
3. Turn off "Restricted mode"
4. Click "Browse" and then the folder icon
5. Copy the plugin files to your vault:

```bash
# Find your vault path (usually ~/Documents/YourVault)
VAULT_PATH=~/Documents/YourVault

# Create plugin directory
mkdir -p "$VAULT_PATH/.obsidian/plugins/zotero-ai-assistant"

# Copy plugin files
cp ~/zotero-obsidian-ai/obsidian-plugin/main.js "$VAULT_PATH/.obsidian/plugins/zotero-ai-assistant/"
cp ~/zotero-obsidian-ai/obsidian-plugin/manifest.json "$VAULT_PATH/.obsidian/plugins/zotero-ai-assistant/"
```

6. Reload Obsidian (Ctrl/Cmd + R)
7. Go to Settings → Community plugins
8. Enable "Zotero AI Research Assistant"

## Step 5: Configure the Plugin

1. Go to Settings → Zotero AI Research Assistant
2. Enter your configuration:
   - **Backend URL**: `http://localhost:8000`
   - **Zotero API Key**: Your API key from Step 2
   - **Library ID**: Your library ID from Step 2
   - **Library Type**: Usually "user"
   - **Notes Folder**: Where to save papers (e.g., "Research Papers")
   - **Maintain Library Structure**: Toggle on to mirror Zotero collections

## Step 6: Test the Integration

1. Add a test paper to Zotero
2. In Obsidian, click the sync icon in the ribbon or use command palette
3. The paper should appear in your configured folder
4. Open the paper note and try the Q&A feature

## Running as a Service (Optional)

### Linux/macOS (using systemd)

Create service file:

```bash
sudo nano /etc/systemd/system/zotero-ai.service
```

Add:

```ini
[Unit]
Description=Zotero-Obsidian AI Backend
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/home/yourusername/zotero-obsidian-ai/backend
Environment="PATH=/home/yourusername/zotero-obsidian-ai/backend/venv/bin"
ExecStart=/home/yourusername/zotero-obsidian-ai/backend/venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable zotero-ai
sudo systemctl start zotero-ai
sudo systemctl status zotero-ai
```

### Windows (using NSSM)

1. Download NSSM from https://nssm.cc
2. Install the service:

```cmd
nssm install ZoteroAI "C:\path\to\python.exe" "C:\path\to\zotero-obsidian-ai\backend\main.py"
nssm start ZoteroAI
```

## Customizing Prompts

Edit the prompt templates in `/config/prompts/paper_analysis.yaml` to customize how papers are analyzed. You can:

- Modify the main analysis prompt
- Add custom analysis types
- Change summary formats
- Adjust Q&A behavior

After editing, either:
- Restart the backend service, or
- Use the "Edit analysis prompts" command in Obsidian

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (needs 3.9+)
- Verify all dependencies installed: `pip list`
- Check `.env` file exists and has correct values
- Look at logs in `~/zotero-obsidian-ai/logs/backend.log`

### Can't connect to Zotero
- Verify API key is correct
- Check library ID (it's your userID, not username)
- Ensure Zotero sync is enabled
- Try accessing https://api.zotero.org/users/YOUR_ID/items with your API key

### Bedrock errors
- Verify AWS credentials: `aws sts get-caller-identity`
- Check Bedrock model access is approved
- Ensure region is correct in `.env`
- Try a different model ID if needed

### Obsidian plugin not working
- Check console for errors (Ctrl+Shift+I)
- Verify backend is running
- Check backend URL in settings
- Try manual sync first

### PDFs not processing
- Ensure Zotero file sync is enabled
- Check PDF exists in Zotero
- Verify enough disk space for cache
- Look for download errors in backend logs

## Performance Tuning

### For large libraries
- Increase `SYNC_DAYS_BACK` to limit initial sync
- Adjust `CHUNK_SIZE` for better text processing
- Consider using a faster Bedrock model

### For better analysis
- Use Claude 3 Opus for highest quality
- Increase `MAX_TOKENS` for longer responses
- Customize prompts for your field

## Support

For issues or questions:
1. Check the logs in `~/zotero-obsidian-ai/logs/`
2. Review error messages in Obsidian console
3. Ensure all services are running
4. Verify API credentials are valid