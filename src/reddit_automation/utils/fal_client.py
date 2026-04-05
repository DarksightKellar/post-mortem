"""fal.ai API client for image generation."""

import json
import os
import time
import urllib.request
import urllib.error


class FalClient:
    """Client for fal.ai image generation API.
    
    Uses the fal.ai REST API to submit image generation requests,
    poll for completion, and download results.
    """

    def __init__(self, api_key: str = None, config: dict = None):
        self.api_key = api_key or os.environ.get("FAL_KEY")
        if not self.api_key:
            raise ValueError("FAL_KEY environment variable or api_key is required")
        
        fal_config = (config or {}).get("fal", {})
        self.model = fal_config.get("model", "fal-ai/flux/schnell")
        self.base_url = "https://fal.run"

    def _submit(self, prompt: str) -> str:
        """Submit an image generation request and return the request ID."""
        url = f"{self.base_url}/{self.model}"
        payload = json.dumps({"prompt": prompt}).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Key {self.api_key}",
            },
            method="POST",
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        
        return data["request_id"]

    def _check_status(self, request_id: str, request_id_field: str = None) -> dict:
        """Check the status of a generation request."""
        # The status endpoint is at https://fal.ai/api/queue/{model}/requests/{request_id}/status
        # but fal.run uses a polling endpoint. For simplicity, we use the queue status endpoint.
        model_slug = self.model.replace("fal-ai/", "")
        url = f"https://queue.fal.run/{self.model}/requests/{request_id}/status"
        
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Key {self.api_key}",
            },
        )
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def _get_result(self, request_id: str) -> dict:
        """Get the result of a completed generation request."""
        url = f"https://queue.fal.run/{self.model}/requests/{request_id}"
        
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Key {self.api_key}",
            },
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def download_image(self, image_url: str, output_path: str) -> str:
        """Download an image from a URL to a local file path."""
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        req = urllib.request.Request(image_url)
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        
        with open(output_path, "wb") as f:
            f.write(data)
        
        return output_path

    def generate(self, prompt: str, output_path: str, max_retries: int = 30, poll_interval: float = 2.0) -> str:
        """Generate an image synchronously.
        
        1. Submit the prompt
        2. Poll until completed
        3. Download the image
        
        Returns the output path on success.
        """
        request_id = self._submit(prompt)
        
        for attempt in range(max_retries):
            status = self._check_status(request_id)
            
            if status.get("status") == "COMPLETED":
                result = self._get_result(request_id)
                images = result.get("images", [])
                if not images:
                    raise RuntimeError(f"No images in result for request {request_id}")
                
                image_url = images[0]["url"]
                self.download_image(image_url, output_path)
                return output_path
            
            elif status.get("status") == "ERROR":
                detail = status.get("detail", "unknown error")
                raise RuntimeError(f"fal.ai generation failed: {detail}")
            
            # Still in progress, wait and retry
            time.sleep(poll_interval)
        
        raise RuntimeError(f"fal.ai generation timed out after {max_retries} attempts")
