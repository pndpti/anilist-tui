#!/bin/sh

set -e

if ! command -v uv >/dev/null 2>&1
then
    echo "uv is not installed. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "uv installation complete!"
    echo ""

    if [ -x ~/.local/bin/uv ]; then
        ~/.local/bin/uv tool install -U anilist-tui --python 3.12
    else
        echo "Please restart your shell and run this script again"
        echo ""
        exit 0
    fi

else
    uv self update
    uv tool install -U anilist-tui --python 3.12
fi

echo ""
echo "anilist-tui is installed!"
echo "Run 'anilist-tui' to launch"
echo ""
echo "For help and support, visit:"
echo "https://github.com/pndpti/anilist-tui/discussions"
echo ""
