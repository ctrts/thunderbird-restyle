-- Trance: azure -> violet uplift sweep on the focused window, with a soft azure bloom.
local active_border_color = { colors = { "rgba(38d6ffcc)", "rgba(a97bffcc)" }, angle = 45 }
local inactive_border_color = "rgba(1a2340aa)"

hl.config({
  general = {
    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    },
  },

  group = {
    col = {
      border_active = active_border_color,
      border_inactive = inactive_border_color,
    },
  },

  decoration = {
    shadow = {
      enabled = true,
      range = 14,
      render_power = 3,
      color = "rgba(38d6ff42)",
      color_inactive = "rgba(00000066)",
    },
  },
})
