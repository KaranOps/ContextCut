import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Accept': 'application/json',
    },
});

/**
 * Upload B-roll video files
 * @param {File[]} files - Array of video files
 * @param {function} onProgress - Progress callback
 */
export const uploadBRoll = async (files, onProgress) => {
    const formData = new FormData();
    files.forEach((file) => {
        formData.append('files', file);
    });

    const response = await apiClient.post('/upload-broll', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
            if (onProgress && progressEvent.total) {
                const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(percent);
            }
        },
    });

    return response.data;
};

/**
 * Process A-roll and generate timeline
 * @param {File} file - A-roll video file
 * @param {function} onProgress - Progress callback
 */
export const processTimeline = async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/process-timeline', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
            if (onProgress && progressEvent.total) {
                const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(percent);
            }
        },
    });

    return response.data;
};

/**
 * Poll task status
 * @param {string} taskId - Task ID to poll
 */
export const getTaskStatus = async (taskId) => {
    const response = await apiClient.get(`/status/${taskId}`);
    return response.data;
};

/**
 * Poll task status until complete or failed
 * @param {string} taskId - Task ID to poll
 * @param {function} onStatusChange - Called when status changes
 * @param {number} interval - Poll interval in ms
 */
export const pollTaskStatus = (taskId, onStatusChange, interval = 2000) => {
    let isPolling = true;

    const poll = async () => {
        while (isPolling) {
            try {
                const status = await getTaskStatus(taskId);
                onStatusChange(status);

                if (status.status === 'completed' || status.status === 'failed') {
                    isPolling = false;
                    break;
                }
            } catch (error) {
                console.error('Polling error:', error);
                onStatusChange({ status: 'failed', error: error.message });
                isPolling = false;
                break;
            }

            await new Promise((resolve) => setTimeout(resolve, interval));
        }
    };

    poll();

    // Return cancel function
    return () => {
        isPolling = false;
    };
};

/**
 * Fetch result JSON from URL
 * @param {string} url - URL to fetch
 */
export const fetchResult = async (url) => {
    const response = await axios.get(url);
    return response.data;
};

export default apiClient;
