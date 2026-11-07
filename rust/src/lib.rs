use axum::{extract::Json, http::StatusCode};
use serde::{Deserialize, Serialize};
use utoipa::{OpenApi, ToSchema};
use utoipa_axum::{router::OpenApiRouter, routes};

#[derive(Debug, Deserialize, ToSchema)]
pub struct AddRequest {
    /// The first operand.
    pub a: i64,
    /// The second operand.
    pub b: i64,
}

#[derive(Debug, Serialize, ToSchema)]
pub struct AddResponse {
    /// The sum of `a` and `b`.
    pub result: i64,
}

/// Add two integers.
#[utoipa::path(
    post,
    path = "/add",
    request_body = AddRequest,
    responses(
        (status = 200, description = "The sum of the two operands.", body = AddResponse)
    )
)]
pub async fn add(Json(request): Json<AddRequest>) -> (StatusCode, Json<AddResponse>) {
    (
        StatusCode::OK,
        Json(AddResponse {
            result: request.a + request.b,
        }),
    )
}

#[derive(OpenApi)]
#[openapi(
    info(
        title = "Embedded CI/CD API",
        version = "0.1.0",
        description = "API provided by the embedded-cicd Rust service."
    ),
    components(schemas(AddRequest, AddResponse))
)]
pub struct ApiDoc;

/// Build the application router and collect its OpenAPI paths at the same time.
pub fn api_router() -> OpenApiRouter {
    OpenApiRouter::with_openapi(ApiDoc::openapi()).routes(routes!(add))
}
