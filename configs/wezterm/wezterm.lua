---@diagnostic disable: undefined-doc-name, undefined-field
-- Pull in the wezterm API
---@type Wezterm
local wezterm = require("wezterm")
-- local mappings = require("wz-mappings")
---@type Config
local cf = wezterm.config_builder()
-- This will hold the configuration.

-- This is where you actually apply your config choices
local config = {
	automatically_reload_config = true,
	color_scheme = 'tokyonight',
	font = wezterm.font_with_fallback({ "JetBrainsMono NFP", "Hack Nerd Font" }),
	font_size = 10,
	window_background_opacity = 0.9,
	win32_system_backdrop = "Acrylic",
	window_padding = {
		left = "5px",
	},
	disable_default_key_bindings = true,
	-- default_domain = "WSL:Ubuntu",
	window_decorations = "INTEGRATED_BUTTONS|RESIZE",
	use_fancy_tab_bar = false,
	hide_tab_bar_if_only_one_tab = false,
	launch_menu = {},
	min_scroll_bar_height = "0.5cell",
	scrollback_lines = 50000,
	-- enable_tab_bar = false,
	-- enable_scroll_bar = true,
}
-- For example, changing the color scheme:
for k, v in pairs(config) do
	cf[k] = v
end

config.default_prog = { 'pwsh', '-NoLogo' }

-- and finally, return the configuration to wezterm
return config
