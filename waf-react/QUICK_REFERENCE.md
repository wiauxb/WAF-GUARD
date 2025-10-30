# Quick Reference Guide

## What Changed?

### 1️⃣ Config Selection Now Uses LocalStorage
- Selected config persists across browser sessions
- Only analyzed configs can be selected
- Clear visual indicators (ACTIVE badge, ring border, large banner)

### 2️⃣ Real File Browsing Integrated
- Browse actual config files from backend
- Navigate folder structure
- View file contents with syntax highlighting
- Connected to `/config_tree/{config_id}` API

---

## How to Use

### Select a Configuration:
```
1. Upload config ZIP file
2. Click "Analyze" (wait for completion)
3. Click "Select" (only works for analyzed configs)
4. ✅ Config saved to localStorage automatically
```

### Browse Configuration Files:
```
1. Click "View Files" on any config
2. Navigate folders by clicking them
3. Click "Back" to go to parent folder
4. Click files to view content
5. Monaco editor shows content with syntax highlighting
```

---

## Visual Guide

### Selected Config Display:
```
┌─────────────────────────────────────────────────────┐
│ 🔵 Active Configuration                             │
│                                                     │
│ Production WAF Config                    ✓ Analyzed│
│ ID: 22 • Created: Oct 29, 2025  Saved in local... │
└─────────────────────────────────────────────────────┘

┌─────────────────┐ ◄── ACTIVE badge
│  [ACTIVE]       │
│  📄 Production  │
│  ✓ Analyzed     │ ◄── Green badge
│  ID: 22         │
│                 │
│ [✓ Selected]    │ ◄── Button shows selected
└─────────────────┘
    ▲ Ring border
```

### File Browser Layout:
```
┌──────────────────────────────────────────────┐
│  Production Config - Files / conf.d          │
├─────────────┬────────────────────────────────┤
│ Files       │                                │
│             │  modsecurity.conf              │
│ 📁 .. (Back)│  ─────────────────             │
│ 📁 conf.d   │  # ModSecurity Config          │
│ 📄 apache.c │  SecRuleEngine On              │
│ 📄 modsec.c │  SecRequestBodyAccess On       │
│             │                                │
│             │  [Save (Read-only)]            │
└─────────────┴────────────────────────────────┘
  File Tree        Monaco Editor
```

---

## LocalStorage Structure

**Key:** `waf-config-storage`

**Value:**
```json
{
  "state": {
    "selectedConfigId": 22
  },
  "version": 0
}
```

**Check it:** DevTools → Application → Local Storage

---

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/configs` | GET | List all configs |
| `/configs/selected` | GET | Get selected config |
| `/configs/select/{id}` | POST | Select config |
| `/configs/analyze/{id}` | POST | Analyze config |
| `/store_config` | POST | Upload config |
| `/config_tree/{id}` | POST | Browse files (FormData: path) |

---

## Status Indicators

| Badge | Meaning | Actions Available |
|-------|---------|-------------------|
| ✓ Analyzed | Config parsed | Select, View Files, Delete |
| ⏱ Pending | Not analyzed | Analyze, View Files, Delete |
| ACTIVE | Currently selected | All actions |

---

## Troubleshooting

### Config won't select?
- ❌ Make sure it's analyzed first (green ✓ badge)
- ❌ Only analyzed configs can be selected

### Files not loading?
- ✅ Check backend is running: `docker-compose up -d`
- ✅ Verify FastAPI is on port 8000
- ✅ Check browser console for errors

### Selection not persisting?
- ✅ Check localStorage in DevTools
- ✅ Make sure cookies/storage not blocked
- ✅ Try different browser if issues persist

### File tree empty?
- ✅ Upload must be a valid ZIP/TAR file
- ✅ Config must be stored in backend
- ✅ Check API response in Network tab

---

## Keyboard Shortcuts (Monaco Editor)

| Key | Action |
|-----|--------|
| `Ctrl+F` | Find in file |
| `Ctrl+H` | Find and replace |
| `Ctrl+/` | Toggle comment |
| `Alt+↑/↓` | Move line up/down |
| `Ctrl+D` | Select next occurrence |

---

## File Type Support

Auto-detected syntax highlighting:

- `.conf`, `.config` → Apache
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
- Others → Apache (default)

---

## Testing Commands

```bash
# Start backend services
cd /home/dassi/wafguard/WAF-GUARD
docker-compose up -d

# Start frontend
cd waf-react
npm run dev

# Check services
docker ps
curl http://localhost:8000/configs
curl http://localhost:8005/health

# Open app
xdg-open http://localhost:8002
```

---

**Need help?** Check the detailed docs:
- `CONFIG_SELECTION_UPDATE.md` - Selection features
- `FILE_TREE_INTEGRATION.md` - File browsing details
- `API_INTEGRATION_COMPLETE.md` - All API endpoints
