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
          overrides = (builtins.fromTOML (builtins.readFile ./rust-toolchain.toml));
        in
        {
          default =
            with pkgs;
            mkShell {
              nativeBuildInputs = [
                cargo
                clippy
                direnv
                hk
                nil
                nixfmt
                rust-analyzer
                rustc
                rustfmt
                yamlfmt
              ];
              buildInputs = [
                openssl
              ];
              env.RUST_SRC_PATH = "${pkgs.rustPlatform.rustLibSrc}";
              env.RUSTC_VERSION = overrides.toolchain.channel;
            };
        }
      );
      formatter = forEachSystem (system: nixpkgs.${system}.nixfmt);
    };
}
