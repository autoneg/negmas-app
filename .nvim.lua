-- Project-local Neovim configuration for negmas-app
-- This file is automatically loaded when opening files in this project

-- Scenario picker using Telescope
local function setup_scenario_picker()
  -- Check if Telescope is available
  local has_telescope, telescope = pcall(require, 'telescope')
  if not has_telescope then
    vim.notify("Telescope not found. Scenario picker requires Telescope.", vim.log.levels.WARN)
    return
  end

  local pickers = require('telescope.pickers')
  local finders = require('telescope.finders')
  local conf = require('telescope.config').values
  local actions = require('telescope.actions')
  local action_state = require('telescope.actions.state')
  local previewers = require('telescope.previewers')

  -- Path to scenarios directory
  local scenarios_path = vim.fn.expand("~/negmas/app/scenarios/")

  -- Function to find all scenario directories
  local function find_scenarios()
    local scenarios = {}
    
    -- Use find command to locate all scenario directories
    -- A scenario directory contains either domain files or utility files
    local handle = io.popen(
      string.format(
        "find '%s' -type f \\( -name '*_domain.yml' -o -name '*domain*.yml' -o -name 'util*.yml' -o -name 'profile*.yml' \\) -exec dirname {} \\; | sort -u",
        scenarios_path
      )
    )
    
    if handle then
      for line in handle:lines() do
        -- Extract scenario name from path
        local name = line:gsub(scenarios_path, ""):gsub("^/", "")
        table.insert(scenarios, {
          name = name,
          path = line,
        })
      end
      handle:close()
    end
    
    return scenarios
  end

  -- Create the picker
  local function scenario_picker(opts)
    opts = opts or {}
    
    local scenarios = find_scenarios()
    
    pickers.new(opts, {
      prompt_title = 'NegMAS Scenarios',
      finder = finders.new_table({
        results = scenarios,
        entry_maker = function(entry)
          return {
            value = entry,
            display = entry.name,
            ordinal = entry.name,
            path = entry.path,
          }
        end,
      }),
      sorter = conf.generic_sorter(opts),
      previewer = previewers.new_buffer_previewer({
        title = "Scenario Info",
        define_preview = function(self, entry, status)
          local path = entry.path
          
          -- Look for info files
          local info_files = {
            path .. "/_info.yaml",
            path .. "/_info.yml",
            path .. "/_stats.yaml",
            path .. "/_stats.yml",
          }
          
          local lines = {}
          table.insert(lines, "Scenario: " .. entry.display)
          table.insert(lines, "Path: " .. path)
          table.insert(lines, "")
          
          -- Try to read info files
          for _, info_file in ipairs(info_files) do
            local f = io.open(info_file, "r")
            if f then
              table.insert(lines, "=== " .. vim.fn.fnamemodify(info_file, ":t") .. " ===")
              for line in f:lines() do
                table.insert(lines, line)
              end
              f:close()
              table.insert(lines, "")
            end
          end
          
          -- List domain and profile files
          local handle = io.popen(string.format("ls -1 '%s' 2>/dev/null", path))
          if handle then
            table.insert(lines, "=== Files ===")
            for file in handle:lines() do
              if file:match("%.yml$") or file:match("%.yaml$") then
                table.insert(lines, "  " .. file)
              end
            end
            handle:close()
          end
          
          vim.api.nvim_buf_set_lines(self.state.bufnr, 0, -1, false, lines)
        end,
      }),
      attach_mappings = function(prompt_bufnr, map)
        actions.select_default:replace(function()
          actions.close(prompt_bufnr)
          local selection = action_state.get_selected_entry()
          
          -- Open the scenario directory in file explorer
          vim.cmd("edit " .. selection.path)
        end)
        
        -- Additional mapping to open info file
        map('i', '<C-i>', function()
          local selection = action_state.get_selected_entry()
          actions.close(prompt_bufnr)
          
          -- Try to open _info.yaml or _info.yml
          local info_files = {
            selection.path .. "/_info.yaml",
            selection.path .. "/_info.yml",
          }
          
          for _, info_file in ipairs(info_files) do
            if vim.fn.filereadable(info_file) == 1 then
              vim.cmd("edit " .. info_file)
              return
            end
          end
          
          vim.notify("No info file found for this scenario", vim.log.levels.WARN)
        end)
        
        -- Additional mapping to open stats file
        map('i', '<C-s>', function()
          local selection = action_state.get_selected_entry()
          actions.close(prompt_bufnr)
          
          -- Try to open _stats.yaml or _stats.yml
          local stats_files = {
            selection.path .. "/_stats.yaml",
            selection.path .. "/_stats.yml",
          }
          
          for _, stats_file in ipairs(stats_files) do
            if vim.fn.filereadable(stats_file) == 1 then
              vim.cmd("edit " .. stats_file)
              return
            end
          end
          
          vim.notify("No stats file found for this scenario", vim.log.levels.WARN)
        end)
        
        return true
      end,
    }):find()
  end

  -- Create the command and keymap
  vim.api.nvim_create_user_command('Scenarios', function()
    scenario_picker(require('telescope.themes').get_dropdown({
      previewer = true,
    }))
  end, {})

  -- Map <leader>sS to open scenario picker
  vim.keymap.set('n', '<leader>sS', function()
    scenario_picker(require('telescope.themes').get_dropdown({
      previewer = true,
    }))
  end, { desc = 'Search NegMAS Scenarios' })

  vim.notify("Scenario picker loaded. Use <leader>sS or :Scenarios", vim.log.levels.INFO)
end

-- Setup the picker
setup_scenario_picker()

-- Additional project-specific settings
vim.opt_local.shiftwidth = 2
vim.opt_local.tabstop = 2
vim.opt_local.expandtab = true

-- Python-specific settings for this project
vim.api.nvim_create_autocmd("FileType", {
  pattern = "python",
  callback = function()
    vim.opt_local.shiftwidth = 4
    vim.opt_local.tabstop = 4
  end,
  group = vim.api.nvim_create_augroup("NegmasAppPython", { clear = true }),
})
