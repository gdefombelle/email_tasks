import os
from celery import Celery
from dotenv import load_dotenv
from os import getenv
from pytune_configuration.sync_config_singleton import SimpleConfig, config

if config is None:
    config = SimpleConfig()


class CeleryInitializationError(Exception):
    """
    Exception raised when Celery client initialization fails.
    """
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


# Load configuration from .env
load_dotenv()


class CeleryClient:
    """
    A lightweight Celery client that directly exports task signatures
    and performs a health check at initialization.
    """

    def __init__(self):
        """
        Initialize the Celery client with configuration from .env and perform a health check.
        """

        # Initialize the Celery client
        self.celery_client = Celery(
            "pytune",
            broker=getenv("RABBIT_BROKER_URL", "pyamqp://admin:MyStr0ngP@ss2024!@localhost//"),
            backend=getenv("RABBIT_BACKEND","redis://localhost:6379/0"),
        )

        # Additional configuration
        self.celery_client.conf.update(
            worker_pool=config.RABBIT_WORKER_POOL,
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            broker_transport_options={
                "visibility_timeout": config.RABBIT_VISIBILITY_TIMEOUT
            },
            timezone="UTC",
            enable_utc=True,
        )

        # Expose task signatures
        self.health_check = self.celery_client.signature("email_tasks.health_check")
        self.send_mail = self.celery_client.signature("email_tasks.send_mail")

        # Perform health check during initialization
        try:
            self.health_status = self.check_health()

            if self.health_status["status"] != "OK":
                raise CeleryInitializationError(
                    f"Initialization failed: {self.health_status['message']}"
                )
        except CeleryInitializationError as e:
            print(f"Error during Celery initialization: {e}")
            raise

    def check_health(self):
        """
        Executes the health_check task and returns the result.
        """
        try:
            # Submit the health_check task
            result = self.health_check.delay()
            print(f"Health check task submitted with ID: [{result.id}]")

            # Retrieve the result
            res = result.get(timeout=10)
            print(f"Health check result: {res}")
            return res
        except Exception as e:
            error_message = {
                "status": "ERROR",
                "message": f"Health check task failed: {str(e)}",
            }
            print(error_message)
            return error_message
