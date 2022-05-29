local fn = vim.fn
local install_path = fn.stdpath('data')..'/site/pack/packer/start/packer.nvim'
if fn.empty(fn.glob(install_path)) > 0 then
  packer_bootstrap = fn.system({'git', 'clone', '--depth', '1', 'https://github.com/wbthomason/packer.nvim', install_path})
end

require('packer').startup(function(use)
  -- My plugins here
  use 'wbthomason/packer.nvim' -- Package manager
  use 'tpope/vim-fugitive'
  use 'neovim/nvim-lspconfig' -- Collection of configurations for the built-in LSP client
  use 'fatih/vim-go'
  --use 'ms-jpq/chadtree'
  --use 'ms-jpq/coq_nvim'
  use 'preservim/nerdtree'
  use { 'junegunn/fzf', run = function() vim.fn['fzf#install']() end }
  use { 'nvim-treesitter/nvim-treesitter', run = function() vim.fn['TSUpdate']() end }
  use 'p00f/nvim-ts-rainbow'
  use { 'romgrk/barbar.nvim', requires = {'kyazdani42/nvim-web-devicons'} }
  use { 'nvim-lualine/lualine.nvim', requires = { 'kyazdani42/nvim-web-devicons', opt = true }}
  use 'junegunn/fzf.vim'
  use { 'neoclide/coc.nvim', branch='release'}
  --use({
  --  'ray-x/navigator.lua',
  --  requires = {
  --      { 'ray-x/guihua.lua', run = 'cd lua/fzy && make' },
  --      { 'neovim/nvim-lspconfig' },
  --  },
  --})

  -- Automatically set up your configuration after cloning packer.nvim
  -- Put this at the end after all plugins
  if packer_bootstrap then
    require('packer').sync()
  end
end)

require("nvim-treesitter.configs").setup {
  ensure_installed = {"go", "lua",}, -- one of "all", "maintained" (parsers with maintainers), or a list of languages
  sync_install = false, -- install languages synchronously (only applied to `ensure_installed`)
  ignore_install = { "" }, -- List of parsers to ignore installing
  autopairs = {
    enable = true,
  },
  highlight = {
    enable = true, -- false will disable the whole extension
    disable = { "" }, -- list of language that will be disabled
    additional_vim_regex_highlighting = true,
  },
  indent = { enable = true, disable = { "yaml" } },
  context_commentstring = {
    enable = true,
    enable_autocmd = false,
  },
  rainbow = {
    enable = true,
    -- disable = { "jsx", "cpp" }, list of languages you want to disable the plugin for
    extended_mode = true, -- Also highlight non-bracket delimiters like html tags, boolean or table: lang -> boolean
    max_file_lines = nil, -- Do not enable for files with more than n lines, int
    -- colors = {}, -- table of hex strings
    -- termcolors = {} -- table of colour name strings
  }
}

require('lualine').setup {
  options = {
    icons_enabled = true,
    theme = 'auto',
    component_separators = { left = '', right = ''},
    section_separators = { left = '', right = ''},
    disabled_filetypes = {},
    always_divide_middle = true,
    globalstatus = false,
  },
  sections = {
    lualine_a = {'mode'},
    lualine_b = {'branch', 'diff', 'diagnostics'},
    lualine_c = {'filename'},
    lualine_x = {'encoding', 'fileformat', 'filetype'},
    lualine_y = {'progress'},
    lualine_z = {'location'}
  },
  inactive_sections = {
    lualine_a = {},
    lualine_b = {},
    lualine_c = {'filename'},
    lualine_x = {'location'},
    lualine_y = {},
    lualine_z = {}
  },
  tabline = {},
  extensions = {}
}

-- require'navigator'.setup({
--   transparency = 100, -- 0 ~ 100 blur the main window, 100: fully transparent, 0: opaque,  set to nil or 100 to disable it
--   preview_width = 1.0, -- max width ratio (number of cols for the floating window) / (window width)
--   preview_height = 0.9, -- max list window height, 0.3 by default
-- })
