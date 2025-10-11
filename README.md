# llamaCPPManager

Toolkit for managing local `llama-server` instances (from llama.cpp) on macOS.

## Project Configuration

### Directory Paths

The project uses a `.projectrc` file located in the project root to maintain consistent path references across development and build processes. This file contains environment variables defining key project paths.

**Location**: `/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/.projectrc`

To use these paths in scripts:
```bash
source .projectrc
echo "Project root is at: $PROJECT_ROOT"
echo "GUI Application is at: $APP_PATH"
```

(Rest of the README remains the same)