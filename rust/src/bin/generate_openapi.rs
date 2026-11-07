use api_server::api_router;
use std::{env, fs, io, path::PathBuf};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR")?);
    let output = manifest_dir.join("openapi.json");
    let (_, openapi) = api_router().split_for_parts();
    let json = serde_json::to_string_pretty(&openapi)?;

    fs::write(&output, format!("{json}\n"))
        .map_err(|error| io::Error::new(error.kind(), format!("{}: {error}", output.display())))?;
    println!("generated {}", output.display());
    Ok(())
}
