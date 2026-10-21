#!/usr/bin/env bash
set -euo pipefail

# Install the plugin managers and plugins declared by the original workshop files.
mkdir -p "$HOME/.tmux/plugins" "$HOME/.vim/bundle"
git clone --depth 1 https://github.com/tmux-plugins/tpm.git "$HOME/.tmux/plugins/tpm"
export TMUX_PLUGIN_MANAGER_PATH="$HOME/.tmux/plugins/"
tmux new-session -d -s plugin-install
tmux set-environment -g TMUX_PLUGIN_MANAGER_PATH "$TMUX_PLUGIN_MANAGER_PATH"
trap 'tmux kill-server 2>/dev/null || true' EXIT
"$HOME/.tmux/plugins/tpm/bin/install_plugins"
tmux source-file "$HOME/.tmux.conf"
test -f "$HOME/.tmux/plugins/tmux/nord.tmux"
test -f "$HOME/.tmux/plugins/tmux-sensible/sensible.tmux"
tmux kill-server
trap - EXIT

git clone --depth 1 https://github.com/VundleVim/Vundle.vim.git "$HOME/.vim/bundle/Vundle.vim"
# Bootstrap from the unchanged plugin declarations. The colorscheme is not
# available until PluginInstall finishes, so load the full vimrc afterwards.
bootstrap=$(mktemp)
trap 'rm -f "$bootstrap"' EXIT
printf 'set nocompatible\nfiletype off\n' > "$bootstrap"
sed -n '/^set rtp+=~\/.vim\/bundle\/Vundle.vim/,/^call vundle#end()/p' "$HOME/.vimrc" >> "$bootstrap"
vim -Nu "$bootstrap" -n -es -c 'PluginInstall' -c 'qall!'
# Vundle can report a failed clone without failing Vim. Check every declaration.
python3 - <<'PYTHON'
from pathlib import Path
import re
home = Path.home()
plugins = re.findall(r"^(?:Plugin|Bundle)\s+'([^']+)'", (home / '.vimrc').read_text(), re.M)
for plugin in plugins:
    directory = home / '.vim/bundle' / plugin.split('/')[-1]
    if not (directory / '.git').is_dir():
        raise SystemExit(f'Vim plugin installation failed: {plugin}')
print(f'Installed all {len(plugins)} declared Vim plugins.')
PYTHON
vim -Nu "$HOME/.vimrc" -n -es -c 'qall!'
