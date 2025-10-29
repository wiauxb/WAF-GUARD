# Dialog Component Improvements

## Changes Made

### 1. Dialog Component (`components/ui/dialog.tsx`)

#### Added DialogDescription Component
```tsx
const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
```

#### Added DialogFooter Component
```tsx
const DialogFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn(
      "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
      className
    )}
    {...props}
  />
)
```

#### Improved DialogContent Styling
- **Removed** `grid` layout (caused issues with flex children)
- **Added** `overflow-hidden` for better content handling
- **Changed** to flexible layout system
- **Improved** close button z-index for better stacking

**Before:**
```tsx
className="... grid w-full max-w-lg ... gap-4 ... sm:rounded-lg"
```

**After:**
```tsx
className="... w-full max-w-lg ... rounded-lg overflow-hidden"
```

### 2. Config Page Dialogs (`app/(dashboard)/configs/page.tsx`)

#### Upload Dialog
**Improvements:**
- Added `DialogDescription` for accessibility
- Better spacing with `py-4` and `space-y-2`
- Improved button layout (Cancel + Upload)
- Set max width: `sm:max-w-md`

**Before:**
```tsx
<DialogContent>
  <DialogHeader>
    <DialogTitle>Upload Configuration</DialogTitle>
  </DialogHeader>
  <div className="space-y-4 mt-4">
    {/* fields */}
    <Button className="w-full">Upload</Button>
  </div>
</DialogContent>
```

**After:**
```tsx
<DialogContent className="sm:max-w-md">
  <DialogHeader>
    <DialogTitle>Upload Configuration</DialogTitle>
    <DialogDescription>
      Upload a ZIP or TAR archive containing your WAF configuration files.
    </DialogDescription>
  </DialogHeader>
  <div className="space-y-4 py-4">
    {/* fields with better spacing */}
  </div>
  <div className="flex justify-end gap-3">
    <Button variant="outline">Cancel</Button>
    <Button>Upload</Button>
  </div>
</DialogContent>
```

#### View Config Dialog (Large Dialog)
**Improvements:**
- Used flex layout for proper file tree + editor layout
- Added `max-h-[85vh]` to prevent overflow
- Added border to header separator
- Removed default padding, added custom padding per section
- Better z-index handling

**Before:**
```tsx
<DialogContent className="max-w-6xl h-[80vh]">
  <DialogHeader>...</DialogHeader>
  <div className="flex gap-4 h-full">
    {/* File tree and editor */}
  </div>
</DialogContent>
```

**After:**
```tsx
<DialogContent className="max-w-6xl max-h-[85vh] flex flex-col p-0 gap-0">
  <DialogHeader className="px-6 pt-6 pb-4 border-b">
    <DialogTitle>...</DialogTitle>
    <DialogDescription>...</DialogDescription>
  </DialogHeader>
  <div className="flex gap-4 flex-1 overflow-hidden px-6 pb-6 pt-4">
    {/* File tree and editor */}
  </div>
</DialogContent>
```

### 3. Date Display Hydration Fixes

Added `suppressHydrationWarning` to all date/time displays to prevent hydration mismatches:

**Configs Page:**
```tsx
<CardDescription>
  <span suppressHydrationWarning>
    Created: {formatDate(config.created_at)}
  </span>
</CardDescription>
```

**Chatbot Page:**
```tsx
<p className="text-xs opacity-70" suppressHydrationWarning>
  {formatRelativeTime(thread.updated_at)}
</p>
```

## Benefits

### Accessibility ✅
- All dialogs now have proper ARIA descriptions
- Screen readers can properly announce dialog purpose
- No more console warnings about missing descriptions

### Layout ✅
- Flexible dialog system supports both small and large dialogs
- Proper overflow handling for tall content
- Better spacing and padding consistency
- Large dialogs (like file viewer) display correctly with file tree + editor

### User Experience ✅
- Cancel buttons for user-friendly dialog dismissal
- Better visual hierarchy with descriptions
- Proper scroll behavior for long content
- Improved button layouts (aligned right, proper spacing)

### Developer Experience ✅
- Reusable `DialogFooter` component for consistent button layouts
- Flexible DialogContent that works with any layout system
- Clear pattern for adding descriptions to dialogs
- Easy to customize with className prop

## Usage Examples

### Small Form Dialog
```tsx
<Dialog>
  <DialogContent className="sm:max-w-md">
    <DialogHeader>
      <DialogTitle>Dialog Title</DialogTitle>
      <DialogDescription>Dialog description</DialogDescription>
    </DialogHeader>
    <div className="space-y-4 py-4">
      {/* Form fields */}
    </div>
    <div className="flex justify-end gap-3">
      <Button variant="outline">Cancel</Button>
      <Button>Submit</Button>
    </div>
  </DialogContent>
</Dialog>
```

### Large Custom Layout Dialog
```tsx
<Dialog>
  <DialogContent className="max-w-6xl max-h-[85vh] flex flex-col p-0 gap-0">
    <DialogHeader className="px-6 pt-6 pb-4 border-b">
      <DialogTitle>Large Dialog</DialogTitle>
      <DialogDescription>With custom layout</DialogDescription>
    </DialogHeader>
    <div className="flex-1 overflow-hidden px-6 pb-6 pt-4">
      {/* Custom layout with flex/grid */}
    </div>
  </DialogContent>
</Dialog>
```

## Testing

To verify improvements:
1. Open configs page
2. Click "Upload Configuration" - should show well-spaced form dialog
3. Click "View Files" on a config - should show large dialog with file tree and editor
4. Check browser console - no accessibility warnings
5. Check for hydration errors - none should appear
