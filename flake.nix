{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable-small";
  };
  outputs =
    {
      self,
      nixpkgs,
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
      ];
      forEachSystem = f: nixpkgs.lib.genAttrs systems (system: f system);
      pkgsFor = nixpkgs.legacyPackages;
    in
    {
      devShells = forEachSystem (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default =
            with pkgs;
            mkShell rec {
              nativeBuildInputs = [
                codespell
                direnv
                git
                hk
                nil
                nixfmt
                yamlfmt
              ];
              buildInputs = [
              ];
            };
        }
      );
      formatter = forEachSystem (system: nixpkgs.${system}.nixfmt);
    };
}
