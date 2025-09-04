# Inkscape figure manager.

A script for managing figures done in `inkscape` for typst documents. The base for this script is [insckape-figures](https://github.com/gillescastel/inkscape-figures) done by [Gilles Castel](https://github.com/gillescastel).

## Requirements

You need Python >= 3.7, as well as a picker. Current supported pickers are:

* [rofi](https://github.com/davatorium/rofi) on Linux systems
* [choose](https://github.com/chipsenkbeil/choose) on MacOS

## Installation

You can install it using pip:

```
pip3 install git+https://github.com/DobbiKov/inkscape-figures-typst.git
```

This package currently works on Linux and MacOS. If you're interested in porting it to Windows, feel free to make a pull request.

## Setup

Add the following code to the preamble of your LateX document.

The script assumes the following directory structure:

```
main.tex
figures/
    figure1.svg
    figure2.svg
```

## Usage

* Watch for figures: `inkscape-figures-typst watch`.
* Creating a figure: `inkscape-figures-typst create 'title'`. This uses `~/.config/inkscape-figures-typst/template.svg` as a template.
* Creating a figure in a specific directory: `inkscape-figures-typst create 'title' path/to/figures/`.
* Select figure and edit it: `inkscape-figures-typst edit`.
* Select figure in a specific directory and edit it: `inkscape-figures-typst edit path/to/figures/`.

## Vim mappings

This assumes that you use [TinyMist]([https://github.com/lervag/vimtex](https://github.com/Myriad-Dreamin/tinymist)).

```lua
-- safely get a project root (LSP tinymist → fallback to file’s dir)
local function get_typst_root()
  local bufnr = vim.api.nvim_get_current_buf()
  for _, client in pairs(vim.lsp.get_clients({ bufnr = bufnr })) do
    if client.name == "tinymist" then
      local root = client.config.root_dir
      if root and root ~= "" then
        return root
      end
    end
  end
  -- fallback if LSP didn’t give you anything
  return vim.fn.expand("%:p:h")
end

-- helper to build and run a shell command safely
local function run_cmd(fmt, ...)
  local args = vim.tbl_map(vim.fn.shellescape, { ... })
  local cmd = string.format(fmt, unpack(args))
  vim.cmd(cmd)
end

-- insert‑mode mapping
vim.keymap.set("i", "<C-f>", function()
  local file = vim.fn.expand("%:t")
  if file:match("%.tex$") then
    -- TeX case, using vimtex.root
    run_cmd('silent exec ".!inkscape-figures create %s %s"', 
      vim.fn.getline("."), vim.b.vimtex.root .. "/figures/")
  elseif file:match("%.typ$") then
    -- Typst case, using our safe root
    local root = get_typst_root() .. "/figures/"
    run_cmd('silent exec ".!/Users/dobbikov/Desktop/coding/projects/inkscape-figures/inkscapefigures/main.py create %s %s"',
      vim.fn.getline("."), root)
  end
  vim.cmd("write")
end, { noremap = true, silent = true })

-- normal‑mode mapping
vim.keymap.set("n", "<C-f>", function()
  local file = vim.fn.expand("%:t")
  if file:match("%.tex$") then
    run_cmd('silent exec "!inkscape-figures edit %s > /dev/null 2>&1 &"',
      vim.b.vimtex.root .. "/figures/")
  elseif file:match("%.typ$") then
    local root = get_typst_root() .. "/figures/"
    run_cmd('silent exec ".!/Users/dobbikov/Desktop/coding/projects/inkscape-figures/inkscapefigures/main.py edit %s"',
      root)
  end
  vim.cmd("write")
  vim.cmd("redraw!")
end, { noremap = true, silent = true })
```
The config provided above is compatible with the figure manager provided by [Gilles Castel](https://github.com/gillescastel).

First, run `inkscape-figures-typst watch` in a terminal to setup the file watcher.
Now, to add a figure, type the title on a new line, and press <kbd>Ctrl+F</kbd> in insert mode.
This does the following:

1. Find the directory where figures should be saved depending on which file you're editing and where the main typst file is located, using `tinymist`.
1. Check if there exists a figure with the same name. If there exists one, do nothing; if not, go on.
1. Copy the figure template to the directory containing the figures.
1. In Vim: replace the current line – the line containing figure title – with the LaTeX code for including the figure.
1. Open the newly created figure in Inkscape.
1. Set up a file watcher such that whenever the figure is saved as an svg file by pressing <kbd>Ctrl + S</kbd>, it also gets saved as pdf+LaTeX.

To edit figures, press <kbd>Ctrl+F</kbd> in command mode, and a fuzzy search selection dialog will popup allowing you to select the figure you want to edit.


## Configuration

You can change the default LaTeX template by creating `~/.config/inkscape-figures/config.py` and adding something along the lines of the following:

```python
def typst_template(name, title):
    return '\n'.join((
        f"#import \"figures/{name}.typ\":diagram as {name}",
        f"#{name}()"
        ))
```

## TODO
- [ ] Mappings for VSCode
