{
  description = "Development environment for Math-To-Manim";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, utils }:
    utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        # Libraries required for Manim, Cairo, and Pango
        libs = with pkgs; [
          cairo
          pango
          harfbuzz
          fontconfig
          freetype
          glib
          zlib
          libGL
          stdenv.cc.cc.lib
        ];

        # Build-time tools
        buildTools = with pkgs; [
          pkg-config
          ninja
          meson
          which
          gcc
          python311
          ffmpeg
          texliveFull
          sox
        ];

      in
      {
        devShells.default = pkgs.mkShell {
          nativeBuildInputs = buildTools;
          buildInputs = libs;

shellHook = ''
  echo "--- Math-To-Manim Dev Environment ---"
  
  if [ ! -d ".venv" ]; then
    python -m venv .venv
  fi
  source .venv/bin/activate

  echo "Syncing Python dependencies..."
  pip install --upgrade pip
  pip install Pillow
  pip install rich

  pip install ninja meson-python setuptools wheel gTTS
  pip install google-adk 

  pip install "python-dotenv<0.22" "click<8.2" 
  pip install gtts manim-voiceover

  # Force install of problematic C-extensions with Nix headers
  pip install pycairo manimpango --no-build-isolation || true

  if [ -f requirements.txt ]; then
    pip install -r requirements.txt
  fi
  
  export LD_LIBRARY_PATH=${pkgs.lib.makeLibraryPath (libs ++ buildTools)}:$LD_LIBRARY_PATH

  echo "Ready! All C-extensions (Cairo, Pango, Harfbuzz) are linked."
'';
        };
      }
    );
}
