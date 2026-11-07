use api_server::api_router;
use axum::{extract::Json, routing::get, Router};

#[tokio::main]
async fn main() {
    let (api_router, openapi) = api_router().split_for_parts();
    let app = api_router.merge(
        Router::new().route("/openapi.json", get(|| async { Json(openapi) })),
    );
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("failed to bind server to 0.0.0.0:3000");

    println!("listening on http://{}", listener.local_addr().unwrap());
    axum::serve(listener, app).await.expect("server failed");
}
