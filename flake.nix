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
            mkShell {
              # Development tools; see CONTRIBUTING.md ("Development setup"). rustup installs
              # the compiler pinned in rust-toolchain.toml on first use, so the shell and CI
              # build with the same toolchain.
              nativeBuildInputs = [
                actionlint
                cargo-about
                cargo-deny
                direnv
                hk
                nil
                nixfmt
                python3
                rustup
                yamlfmt
                zizmor
              ];
              buildInputs = [
              ];
              env.HK_PKL_BACKEND = "pklr";
            };
        }
      );
      formatter = forEachSystem (system: nixpkgs.${system}.nixfmt);
    };
}
