"""
Frontend Polling Guide for AI Tutor Backend.
Provides best practices and strategies for efficient polling.
"""

from typing import Dict, Any, Optional
import time

class PollingGuide:
    """Guide for implementing efficient frontend polling."""
    
    @staticmethod
    def get_polling_strategy() -> Dict[str, Any]:
        """
        Get recommended polling strategy for frontend implementation.
        
        Returns:
            Polling configuration and best practices
        """
        return {
            "basic_strategy": {
                "initial_interval_ms": 2000,      # Start with 2 seconds
                "max_interval_ms": 10000,         # Cap at 10 seconds
                "backoff_multiplier": 1.5,        # Increase by 1.5x
                "max_attempts": 180,              # Stop after 6 minutes (average)
                "timeout_after_ms": 300000        # Absolute timeout: 5 minutes
            },
            
            "adaptive_strategy": {
                "description": "Adjust polling based on job status and queue position",
                "queued": {
                    "interval_ms": 5000,           # Poll less frequently when queued
                    "use_queue_position": True     # Adjust based on position
                },
                "rendering": {
                    "interval_ms": 2000,           # Poll more frequently when rendering
                    "max_rendering_time_ms": 180000 # Expect completion within 3 minutes
                }
            },
            
            "error_handling": {
                "network_errors": {
                    "retry_count": 3,
                    "retry_delay_ms": 1000,
                    "exponential_backoff": True
                },
                "rate_limiting": {
                    "respect_429_headers": True,
                    "fallback_delay_ms": 60000     # Wait 1 minute if no header
                },
                "job_not_found": {
                    "retry_count": 2,
                    "then": "assume_expired"
                }
            }
        }
    
    @staticmethod
    def get_javascript_example() -> str:
        """
        Get JavaScript implementation example for polling.
        
        Returns:
            JavaScript code example
        """
        return '''
// Efficient polling implementation for AI Tutor backend
class RenderJobPoller {
    constructor(apiBaseUrl = 'http://localhost:8000') {
        this.apiBaseUrl = apiBaseUrl;
        this.pollingIntervals = new Map(); // Track active polls
    }

    async startPolling(jobId, onUpdate, onComplete, onError) {
        const strategy = {
            initialInterval: 2000,
            maxInterval: 10000,
            backoffMultiplier: 1.5,
            maxAttempts: 180,
            timeoutAfter: 300000
        };

        let attempt = 0;
        let currentInterval = strategy.initialInterval;
        const startTime = Date.now();

        const poll = async () => {
            try {
                // Check for timeout
                if (Date.now() - startTime > strategy.timeoutAfter) {
                    onError(new Error('Polling timeout: job took too long'));
                    return;
                }

                // Check for max attempts
                if (attempt >= strategy.maxAttempts) {
                    onError(new Error('Max polling attempts reached'));
                    return;
                }

                attempt++;

                // Make API call
                const response = await fetch(`${this.apiBaseUrl}/api/render/${jobId}`);
                
                if (response.status === 429) {
                    // Rate limited - wait longer
                    const retryAfter = response.headers.get('Retry-After');
                    const delay = retryAfter ? parseInt(retryAfter) * 1000 : 60000;
                    setTimeout(poll, delay);
                    return;
                }

                if (!response.ok) {
                    if (response.status === 404) {
                        onError(new Error('Job not found - may have expired'));
                        return;
                    }
                    throw new Error(`HTTP ${response.status}`);
                }

                const jobData = await response.json();
                onUpdate(jobData);

                // Check if job is complete
                if (jobData.status === 'ready') {
                    onComplete(jobData);
                    this.stopPolling(jobId);
                    return;
                }

                if (jobData.status === 'error') {
                    onError(new Error(jobData.error || 'Rendering failed'));
                    this.stopPolling(jobId);
                    return;
                }

                // Schedule next poll with backoff
                if (jobData.status === 'queued' || jobData.status === 'rendering') {
                    // Adaptive interval based on status
                    if (jobData.status === 'queued') {
                        currentInterval = Math.min(currentInterval * strategy.backoffMultiplier, strategy.maxInterval);
                    } else {
                        currentInterval = strategy.initialInterval; // Poll faster when rendering
                    }

                    const timeoutId = setTimeout(poll, currentInterval);
                    this.pollingIntervals.set(jobId, timeoutId);
                }

            } catch (error) {
                console.error('Polling error:', error);
                
                // Exponential backoff for network errors
                currentInterval = Math.min(currentInterval * 2, strategy.maxInterval);
                
                if (attempt < 3) {
                    const timeoutId = setTimeout(poll, currentInterval);
                    this.pollingIntervals.set(jobId, timeoutId);
                } else {
                    onError(error);
                }
            }
        };

        // Start polling
        poll();
    }

    stopPolling(jobId) {
        const timeoutId = this.pollingIntervals.get(jobId);
        if (timeoutId) {
            clearTimeout(timeoutId);
            this.pollingIntervals.delete(jobId);
        }
    }

    stopAllPolling() {
        for (const [jobId, timeoutId] of this.pollingIntervals) {
            clearTimeout(timeoutId);
        }
        this.pollingIntervals.clear();
    }
}

// Usage example:
const poller = new RenderJobPoller();

async function renderAnimation(filename, code) {
    try {
        // Start render job
        const renderResponse = await fetch('/api/render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename, code })
        });

        if (!renderResponse.ok) {
            throw new Error('Failed to start render job');
        }

        const { jobId } = await renderResponse.json();

        // Start polling
        poller.startPolling(
            jobId,
            (jobData) => {
                // Update UI with current status
                updateRenderProgress(jobData);
            },
            (jobData) => {
                // Render complete - show video
                showVideo(jobData.videoUrl);
            },
            (error) => {
                // Handle error
                showError(error.message);
            }
        );

    } catch (error) {
        showError(error.message);
    }
}

function updateRenderProgress(jobData) {
    const statusElement = document.getElementById('render-status');
    const progressElement = document.getElementById('render-progress');
    
    statusElement.textContent = `Status: ${jobData.status}`;
    
    if (jobData.status === 'queued') {
        progressElement.textContent = 'Waiting in queue...';
    } else if (jobData.status === 'rendering') {
        progressElement.textContent = 'Rendering animation...';
    }
}

function showVideo(videoUrl) {
    const videoElement = document.getElementById('result-video');
    videoElement.src = videoUrl;
    videoElement.style.display = 'block';
}

function showError(message) {
    const errorElement = document.getElementById('error-message');
    errorElement.textContent = message;
    errorElement.style.display = 'block';
}
'''

    @staticmethod
    def get_react_example() -> str:
        """
        Get React hook implementation example.
        
        Returns:
            React hook code example
        """
        return '''
// React hook for render job polling
import { useState, useEffect, useCallback, useRef } from 'react';

const useRenderJobPolling = (apiBaseUrl = 'http://localhost:8000') => {
    const [jobStatus, setJobStatus] = useState(null);
    const [isPolling, setIsPolling] = useState(false);
    const [error, setError] = useState(null);
    
    const timeoutRef = useRef(null);
    const attemptRef = useRef(0);
    const startTimeRef = useRef(null);

    const stopPolling = useCallback(() => {
        if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
        }
        setIsPolling(false);
    }, []);

    const startPolling = useCallback(async (jobId) => {
        setIsPolling(true);
        setError(null);
        attemptRef.current = 0;
        startTimeRef.current = Date.now();

        const poll = async () => {
            try {
                // Timeout check
                if (Date.now() - startTimeRef.current > 300000) { // 5 minutes
                    setError('Rendering timeout');
                    stopPolling();
                    return;
                }

                attemptRef.current++;

                const response = await fetch(`${apiBaseUrl}/api/render/${jobId}`);
                
                if (response.status === 429) {
                    // Rate limited
                    const retryAfter = response.headers.get('Retry-After');
                    const delay = retryAfter ? parseInt(retryAfter) * 1000 : 60000;
                    timeoutRef.current = setTimeout(poll, delay);
                    return;
                }

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }

                const jobData = await response.json();
                setJobStatus(jobData);

                if (jobData.status === 'ready' || jobData.status === 'error') {
                    stopPolling();
                    if (jobData.status === 'error') {
                        setError(jobData.error || 'Rendering failed');
                    }
                    return;
                }

                // Continue polling
                const interval = jobData.status === 'queued' ? 5000 : 2000;
                timeoutRef.current = setTimeout(poll, interval);

            } catch (err) {
                setError(err.message);
                if (attemptRef.current < 3) {
                    timeoutRef.current = setTimeout(poll, 5000);
                } else {
                    stopPolling();
                }
            }
        };

        poll();
    }, [apiBaseUrl, stopPolling]);

    useEffect(() => {
        return () => {
            stopPolling();
        };
    }, [stopPolling]);

    return {
        jobStatus,
        isPolling,
        error,
        startPolling,
        stopPolling
    };
};

// Usage in component:
const RenderComponent = () => {
    const { jobStatus, isPolling, error, startPolling, stopPolling } = useRenderJobPolling();

    const handleRender = async (filename, code) => {
        try {
            const response = await fetch('/api/render', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename, code })
            });

            const { jobId } = await response.json();
            startPolling(jobId);
        } catch (err) {
            console.error('Render start failed:', err);
        }
    };

    return (
        <div>
            {isPolling && (
                <div>
                    Status: {jobStatus?.status}
                    {jobStatus?.status === 'queued' && <p>Waiting in queue...</p>}
                    {jobStatus?.status === 'rendering' && <p>Rendering...</p>}
                </div>
            )}
            
            {jobStatus?.status === 'ready' && (
                <video src={jobStatus.videoUrl} controls />
            )}
            
            {error && <div className="error">{error}</div>}
            
            <button onClick={() => handleRender('demo', 'code here')}>
                Start Render
            </button>
        </div>
    );
};
'''

# Export singleton instance
polling_guide = PollingGuide()


