# vpype-brush Installation & Distribution Options

## How Python Plugins Work

When you install a Python package with `pip install -e .`, it:
1. Registers the package with Python's package system
2. Creates an "entry point" that vpype can discover
3. Makes the plugin available wherever that Python/vpype is installed

The magic happens in [pyproject.toml](pyproject.toml:20-21):
```toml
[project.entry-points."vpype.plugins"]
brush = "vpype_brush.brush:brush"
```

This tells vpype: "Hey, there's a command called 'brush' available!"

---

## Your Options

### Option 1: Keep Using the Virtual Environment (Current Setup)
**What it is**: Plugin only works when you activate the venv

**How to use**:
```bash
cd /Users/jterraz/Documents/GIT/vpype-brush
source vpype_brush/bin/activate
vpype read input.svg brush -o output.gcode
deactivate
```

**Pros**:
- ✅ Isolated, won't affect other Python projects
- ✅ Already working!

**Cons**:
- ❌ Must activate venv every time
- ❌ Can't use from your vpype_settings scripts easily

---

### Option 2: Install System-Wide (Personal Use)
**What it is**: Install to your system Python so it works everywhere

**How to do it**:
```bash
cd /Users/jterraz/Documents/GIT/vpype-brush
pip3 install -e .
```

Then from ANYWHERE:
```bash
vpype read input.svg brush -o output.gcode
```

**Pros**:
- ✅ Works everywhere, no venv activation needed
- ✅ Can use in your vpype_settings scripts
- ✅ Edits to brush.py take effect immediately (-e flag)

**Cons**:
- ⚠️ Requires vpype to be installed system-wide
- ⚠️ May conflict with other packages (unlikely)

---

### Option 3: Publish to PyPI (Public Package)
**What it is**: Make it installable by anyone with `pip install vpype-brush`

**Steps**:
1. Create GitHub repository
2. Add proper LICENSE (MIT recommended)
3. Test thoroughly
4. Create account on pypi.org
5. Build package: `pip3 install build && python3 -m build`
6. Upload: `pip3 install twine && twine upload dist/*`

Then ANYONE can install:
```bash
pip install vpype-brush
```

**Pros**:
- ✅ Share with the world!
- ✅ Professional distribution
- ✅ Version management
- ✅ Easy updates

**Cons**:
- ⚠️ Requires maintenance
- ⚠️ Need to support users
- ⚠️ More responsibility

---

### Option 4: Submit to vpype Plugin List
**What it is**: Get listed on vpype's official plugin page

**How to do it**:
1. Publish to PyPI first (Option 3)
2. Submit PR to vpype documentation
3. Add entry to plugins list

**See**: https://github.com/abey79/vpype/blob/master/docs/plugins.rst

**Pros**:
- ✅ Discoverable by vpype users
- ✅ Community recognition
- ✅ Feedback and contributors

**Cons**:
- ⚠️ Requires PyPI publication
- ⚠️ Must maintain documentation

---

## Recommended Path Forward

### For Your Immediate Use:
**Do Option 2** - Install system-wide for personal use:
```bash
cd /Users/jterraz/Documents/GIT/vpype-brush
pip3 install -e .
```

This makes it available everywhere on your Mac.

### If You Want to Share:
**Do Options 3 + 4** in sequence:
1. Clean up code (add more tests, examples)
2. Create GitHub repo
3. Publish to PyPI
4. Submit to vpype plugin list

---

## How to Check Your Current vpype Setup

Run these to see what you have:
```bash
# Check if vpype is installed system-wide
which vpype
vpype --version

# Check where Python packages are installed
pip3 show vpype
```

If vpype ISN'T installed system-wide, you'll need to install it first:
```bash
pip3 install vpype
```

Then install your plugin:
```bash
cd /Users/jterraz/Documents/GIT/vpype-brush
pip3 install -e .
```

---

## What Happens When You Install

When you run `pip3 install -e .`:

1. **Reads pyproject.toml** - Gets package info and dependencies
2. **Installs dependencies** - Installs vpype, click, numpy, shapely if missing
3. **Creates entry point** - Registers the "brush" command
4. **Creates symlink** - Points to your source code (the `-e` flag)
5. **Registers with vpype** - Plugin automatically discovered

The `-e` flag means "editable" - any changes to brush.py take effect immediately without reinstalling!

---

## Testing After Installation

After installing system-wide:
```bash
# Should show the brush command
vpype --help | grep brush

# Should work from any directory
cd ~
vpype read /path/to/file.svg brush -o output.gcode
```

---

## Next Steps

Let me know which option you want to pursue:

1. **Just make it work for me** → I'll help you install system-wide (Option 2)
2. **I want to publish it** → I'll help you prepare for PyPI (Option 3)
3. **Both!** → We'll do them in sequence

What would you like to do?
