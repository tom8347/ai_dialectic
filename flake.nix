{
  description = "Claude Dialogue Runner — run two Claude instances in conversation";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
  let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };

    py = pkgs.python3.withPackages (ps: with ps; [
      pynvim
      python-lsp-server
      pylsp-mypy
      pylsp-rope
      ipython
      anthropic
      pyyaml
      rich
      pypdf
    ]);
  in
  {
    devShells.${system}.default = pkgs.mkShell {
      packages = [ py ];

      shellHook = ''
        echo "Claude Dialogue Runner"
        echo "  python  $(python --version)"
        echo "  anthropic $(python -c 'import anthropic; print(anthropic.__version__)')"
        RICH_VER=$(python -c 'from importlib.metadata import version; print(version("rich"))')
        echo "  rich    $RICH_VER"
      '';
    };
  };
}
