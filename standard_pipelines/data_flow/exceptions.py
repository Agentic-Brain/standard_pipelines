class InvalidWebhookError(RuntimeError):
    pass


class APIError(RuntimeError):
    pass


class RetriableAPIError(APIError):
    pass