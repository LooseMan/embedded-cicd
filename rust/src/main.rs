use axum::{extract::Json, http::StatusCode, routing::post, Router};
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct AddRequest {
    a: i64,
    b: i64,
}

#[derive(Debug, Serialize)]
struct AddResponse {
    result: i64,
}

async fn add(Json(request): Json<AddRequest>) -> (StatusCode, Json<AddResponse>) {
    (
        StatusCode::OK,
        Json(AddResponse {
            result: request.a + request.b,
        }),
    )
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/add", post(add));
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000")
        .await
        .expect("failed to bind server to 0.0.0.0:3000");

    println!("listening on http://{}", listener.local_addr().unwrap());
    axum::serve(listener, app).await.expect("server failed");
}
