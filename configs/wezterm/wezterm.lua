local wezterm = require("wezterm")
local config = wezterm.config_builder()
wezterm.log_info("reloading")

require("tabs").setup(config)
require("mouse").setup(config)
require("links").setup(config)
require("keys").setup(config)

config.enable_wayland = true
config.webgpu_power_preference = "HighPerformance"
-- config.animation_fps = 1
config.cursor_blink_ease_in = "Constant"
config.cursor_blink_ease_out = "Constant"

config.color_scheme = "dream"

config.underline_thickness = 3
config.cursor_thickness = 0.5
config.underline_position = -6

if wezterm.target_triple:find("windows") then
	config.default_prog = { "pwsh", "-NoLogo" }
	config.window_decorations = "RESIZE"
	-- config.window_decorations = "TITLE | RESIZE"
	-- config.window_background_opacity = 0.9
	-- config.win32_system_backdrop = 'Acrylic'
	wezterm.on("gui-startup", function(cmd)
		local screen = wezterm.gui.screens().active
		local tab, pane, window = wezterm.mux.spawn_window(cmd or {})
		local gui = window:gui_window()
		local width = 0.8 * screen.width
		local height = 0.8 * screen.height
		gui:set_inner_size(width, height)
		gui:set_position((screen.width - width) / 2, (screen.height - height) / 2)
	end)
else
	config.term = "wezterm"
	config.window_decorations = "NONE"
end

config.automatically_reload_config = true

config.font_size = 9.0
config.font = wezterm.font_with_fallback({
	{ family = "PitagonSansM Nerd Font Propo", weight = "Medium" },
	{ family = "JetBrainsMono NFP", weight = "Medium" },
	"Noto Color Emoji",
})

config.bold_brightens_ansi_colors = true
config.freetype_load_target = "Normal"
config.line_height = 1.0

config.default_cursor_style = "BlinkingBar"
config.force_reverse_video_cursor = true
config.window_padding = { left = 12, right = 12, top = 12, bottom = 12 }

config.scrollback_lines = 10000

return config
