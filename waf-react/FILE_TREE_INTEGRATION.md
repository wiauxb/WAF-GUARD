# Configuration File Tree Integration ✅

## Overview

Integrated the `/config_tree/{config_id}` API endpoint from `storage.py` to enable real-time browsing and viewing of configuration files stored in the backend.

## Changes Made

### 1. **Added TypeScript Types**

**File:** `types/index.ts`

```typescript
export interface ConfigContent {
  filename: string
  is_folder: boolean
  file_content?: string | null
}
```

This matches the Pydantic model from `models.py`:
```python
class ConfigContent(BaseModel):
    filename: str
    is_folder: bool
    file_content: Optional[str] = None
```

### 2. **Enhanced Config Page State Management**

**File:** `app/(dashboard)/configs/page.tsx`

Added new state variables:
- `currentPath` - Tracks current directory path
- `fileTree` - Stores list of files/folders in current directory
- `isLoadingFiles` - Loading state for file operations
- `selectedFilePath` - Full path of currently selected file

### 3. **Implemented File Tree Navigation**

#### `loadConfigFiles(configId, path)`
- Fetches files/folders from backend at specified path
- Uses GET `/config_tree/{config_id}?path={path}`
- Updates file tree display
- Handles loading states and errors

#### `handleFileClick(item)`
- **For folders**: Navigates into folder, loads contents
- **For files**: Loads file content and displays in Monaco editor

#### `handleBackNavigation()`
- Navigates to parent directory
- Splits current path and removes last segment

#### `renderFileTree()`
- Displays current directory contents
- Shows "Back" button when not in root
- Distinguishes folders (📁 blue) from files (📄 gray)
- Loading spinner during API calls

### 4. **Dynamic Language Detection**

**Function:** `getLanguageFromFilename(filename)`

Maps file extensions to Monaco editor languages:
- `.conf`, `.config`, `.htaccess` → Apache syntax
- `.json` → JSON
- `.xml` → XML
- `.yaml`, `.yml` → YAML
- `.sh`, `.bash` → Shell
- `.py` → Python
- `.js` → JavaScript
- `.ts` → TypeScript
- `.html` → HTML
- `.css` → CSS
- `.md` → Markdown
- Default → Apache (for ModSecurity configs)

### 5. **Enhanced UI/UX**

#### File Tree Panel:
- Shows current path in header: `Files / path/to/directory`
- "Back" button with folder icon for navigation
- Color-coded icons:
  - 🔵 Blue folder icon for directories
  - ⚪ Gray file icon for files
- Hover effects for better interactivity

#### Editor Panel:
- Displays full file path in header
- "Save Changes (Read-only)" button (disabled) - indicates view-only mode
- Auto-detects syntax highlighting based on file extension
- Empty state with helpful message when no file selected

#### Loading States:
- Spinner shows while fetching files
- Prevents multiple simultaneous requests
- Error handling with toast notifications

## API Integration

### Backend Endpoint Analysis

From `storage.py`:
```python
@router.post("/config_tree/{config_id}")
async def config_tree(config_id: int, path: str = Form(...)) -> List[ConfigContent]:
```

**How it works:**
1. Receives POST request with `path` as Form data parameter
2. Reads config info from `/tmp/config_{config_id}_info.json`
3. Constructs full path from config base + relative path
4. If path is a file: Returns single item with `file_content`
5. If path is a folder: Returns list of items with `is_folder` flag
6. Each item has `filename`, `is_folder`, and optionally `file_content`

### Frontend Implementation

```typescript
// Load directory contents
const formData = new FormData()
formData.append('path', path || '')

const response = await webAppApi.post<ConfigContent[]>(
  `/config_tree/${configId}`,
  formData,
  {
    headers: { 'Content-Type': 'multipart/form-data' }
  }
)

// For files: response.data[0].file_content contains the content
// For folders: response.data is an array of ConfigContent items
```

## User Workflow

### Viewing Configuration Files:

1. **Navigate to Configs page**
2. **Click "View Files"** on any configuration card
3. **Dialog opens** with file tree on left, editor on right
4. **Browse folders:**
   - Click folder to navigate into it
   - Path updates: `Files / conf.d`
   - Click ".. (Back)" to go up one level
5. **View files:**
   - Click any file to load its content
   - Monaco editor displays with proper syntax highlighting
   - Full file path shown in header
6. **Navigate freely:**
   - Folder structure is fully browsable
   - Back button maintains navigation history
   - Real-time loading from backend

## Features

### ✅ Complete File System Navigation
- Browse entire configuration directory structure
- Navigate into nested folders
- Go back to parent directories
- Root directory listing

### ✅ Real-time File Viewing
- Fetch file content on-demand from backend
- No local caching (always fresh data)
- Proper encoding handling

### ✅ Syntax Highlighting
- Auto-detects file type from extension
- Supports 10+ languages/formats
- Defaults to Apache config syntax

### ✅ Professional UI
- Split-panel layout (tree + editor)
- Clear visual hierarchy
- Responsive design
- Loading indicators
- Error handling with user feedback

### ✅ Read-only Mode
- Files are view-only (no accidental edits)
- "Save Changes" button disabled
- Clear indication of read-only state

## Example API Responses

### Root Directory (Empty Path):
**Request:** `POST /config_tree/22` with FormData: `path=""`

**Response:**
```json
[
  {
    "filename": "apache2.conf",
    "is_folder": false
  },
  {
    "filename": "conf.d",
    "is_folder": true
  },
  {
    "filename": "modsecurity.conf",
    "is_folder": false
  }
]
```

### Subdirectory:
**Request:** `POST /config_tree/22` with FormData: `path="conf.d"`

**Response:**
```json
[
  {
    "filename": "security.conf",
    "is_folder": false
  },
  {
    "filename": "ssl.conf",
    "is_folder": false
  }
]
```

### File Content:
**Request:** `POST /config_tree/22` with FormData: `path="modsecurity.conf"`

**Response:**
```json
[
  {
    "filename": "modsecurity.conf",
    "is_folder": false,
    "file_content": "# ModSecurity Configuration\nSecRuleEngine On\nSecRequestBodyAccess On\n..."
  }
]
```

## Error Handling

### File Not Found:
```
Toast: "Failed to load files"
Console: Error details logged
User remains in current directory
```

### Invalid Path:
```
Backend returns 404
Toast displays error message
File tree remains unchanged
```

### Network Issues:
```
Loading spinner shows
Timeout after 60s (axios default)
Error toast appears
User can retry
```

## Testing

### Test the Integration:

1. **Start Docker services:**
   ```bash
   cd /home/dassi/wafguard/WAF-GUARD
   docker-compose up -d
   ```

2. **Start Next.js app:**
   ```bash
   cd waf-react
   npm run dev
   ```

3. **Test file browsing:**
   - Go to http://localhost:8002/configs
   - Upload a configuration ZIP file
   - Click "View Files" on the uploaded config
   - Navigate through folders
   - Click files to view content
   - Test "Back" navigation

### Verify API Calls:

Open browser DevTools → Network tab:
- Look for calls to `/config_tree/22?path=...`
- Verify parameters are correct
- Check response structure matches `ConfigContent[]`

## Future Enhancements

### Possible Additions:
- ✏️ **Edit Mode** - Allow saving file changes back to backend
- 🔍 **Search** - Search within files or file names
- 📥 **Download** - Download individual files or entire config
- 📊 **Diff View** - Compare files between configurations
- 🔖 **Bookmarks** - Mark frequently accessed files
- 🌳 **Tree View** - Collapsible folder tree instead of navigation
- 📝 **Syntax Validation** - Real-time Apache/ModSecurity syntax checking

## Benefits

✅ **Real Backend Integration** - No more mock data
✅ **Live File System** - Browse actual uploaded configs
✅ **Professional UX** - Intuitive folder navigation
✅ **Syntax Aware** - Proper highlighting for all file types
✅ **Error Resilient** - Graceful error handling
✅ **Performance** - Only loads files on-demand
✅ **Scalable** - Works with any size configuration

---

**Status:** ✅ Fully Implemented and Ready for Testing
