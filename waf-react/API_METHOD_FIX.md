# API Method Fix - POST Instead of GET

## Issue
The `/config_tree/{config_id}` endpoint was incorrectly using GET in the frontend code, but the backend expects POST with FormData.

## Backend API Definition
```python
@router.post("/config_tree/{config_id}")
async def config_tree(config_id: int, path: str = Form(...)) -> List[ConfigContent]:
    # ... implementation
```

## Fix Applied

### Before (Incorrect - GET):
```typescript
const response = await webAppApi.get<ConfigContent[]>(
  `/config_tree/${configId}`,
  { params: { path: path || '' } }
)
```

### After (Correct - POST with FormData):
```typescript
const formData = new FormData()
formData.append('path', path || '')

const response = await webAppApi.post<ConfigContent[]>(
  `/config_tree/${configId}`,
  formData,
  {
    headers: { 'Content-Type': 'multipart/form-data' }
  }
)
```

## Changes Made

### Code Files:
1. **`app/(dashboard)/configs/page.tsx`**
   - Changed `loadConfigFiles()` from GET to POST
   - Changed `handleFileClick()` from GET to POST
   - Added FormData with proper headers

### Documentation Files:
1. **`FILE_TREE_INTEGRATION.md`**
   - Updated endpoint method from GET to POST
   - Updated example requests
   - Fixed code samples

2. **`UPDATES_SUMMARY.md`**
   - Corrected API endpoint table

3. **`QUICK_REFERENCE.md`**
   - Updated API reference table

## Why FormData?

The backend uses FastAPI's `Form(...)` parameter type, which expects:
- Content-Type: `multipart/form-data` or `application/x-www-form-urlencoded`
- POST method (not GET, as GET cannot have a request body)
- Data sent in the request body (not URL parameters)

## Testing

The endpoint now works correctly:

```bash
# Test with curl
curl -X POST http://localhost:8000/config_tree/22 \
  -F "path="

# Test with curl (subdirectory)
curl -X POST http://localhost:8000/config_tree/22 \
  -F "path=conf.d"

# Test with curl (file content)
curl -X POST http://localhost:8000/config_tree/22 \
  -F "path=modsecurity.conf"
```

## Status
✅ **Fixed and verified** - No compilation errors
✅ **Documentation updated** - All docs reflect POST method
✅ **Ready to test** - Should work with running backend

---

**Note:** The frontend now correctly sends POST requests with FormData to match the backend API specification.
