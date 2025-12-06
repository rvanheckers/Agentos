/**
 * MomentSelector Tests
 * Unit tests for the MomentSelector component
 */

import { MomentSelector } from './MomentSelector.js';

// Mock fetch globally for tests
global.fetch = jest.fn();

describe('MomentSelector', () => {
    let selector;
    const mockJobId = 'test-job-123';

    beforeEach(() => {
        selector = new MomentSelector(mockJobId);
        selector.moments = [
            {
                id: 'moment-1',
                moment_index: 0,
                start_time: 6.2,
                end_time: 52.1,
                duration: 45.9,
                description: 'Test moment 1',
                sentence_text: 'This is a test',
                keywords: ['test', 'moment'],
                viral_score: 85,
                is_selected: false
            },
            {
                id: 'moment-2',
                moment_index: 1,
                start_time: 65.0,
                end_time: 95.0,
                duration: 30.0,
                description: 'Test moment 2',
                viral_score: 72,
                is_selected: false
            }
        ];

        // Reset fetch mock
        fetch.mockClear();
    });

    describe('Initialization', () => {
        it('should initialize with correct properties', () => {
            expect(selector.jobId).toBe(mockJobId);
            expect(selector.apiBaseUrl).toBe('/api');
            expect(selector.moments).toHaveLength(2);
            expect(selector.selectedIndices).toBeInstanceOf(Set);
            expect(selector.selectedIndices.size).toBe(0);
        });

        it('should accept custom API base URL', () => {
            const customSelector = new MomentSelector(mockJobId, '/custom-api');
            expect(customSelector.apiBaseUrl).toBe('/custom-api');
        });
    });

    describe('fetchMoments', () => {
        it('should fetch moments successfully', async () => {
            const mockResponse = {
                job_id: mockJobId,
                total_moments: 2,
                moments: selector.moments
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await selector.fetchMoments();

            expect(result.ready).toBe(true);
            expect(result.data.total_moments).toBe(2);
            expect(selector.moments).toHaveLength(2);
            expect(fetch).toHaveBeenCalledWith('/api/jobs/test-job-123/moments');
        });

        it('should handle 400 error (not ready)', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 400
            });

            const result = await selector.fetchMoments();

            expect(result.ready).toBe(false);
            expect(result.message).toContain('not ready');
        });

        it('should handle 404 error', async () => {
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 404
            });

            await expect(selector.fetchMoments()).rejects.toThrow('Job not found');
        });

        it('should handle network errors', async () => {
            fetch.mockRejectedValueOnce(new Error('Network error'));

            await expect(selector.fetchMoments()).rejects.toThrow('Network error');
        });
    });

    describe('toggleMoment', () => {
        it('should add moment to selection', () => {
            selector.toggleMoment(0);
            expect(selector.selectedIndices.has(0)).toBe(true);
            expect(selector.selectedIndices.size).toBe(1);
        });

        it('should remove moment from selection', () => {
            selector.selectedIndices.add(0);
            selector.toggleMoment(0);
            expect(selector.selectedIndices.has(0)).toBe(false);
            expect(selector.selectedIndices.size).toBe(0);
        });

        it('should toggle multiple moments', () => {
            selector.toggleMoment(0);
            selector.toggleMoment(1);
            expect(selector.selectedIndices.size).toBe(2);

            selector.toggleMoment(0);
            expect(selector.selectedIndices.size).toBe(1);
            expect(selector.selectedIndices.has(1)).toBe(true);
        });
    });

    describe('selectAll', () => {
        it('should select all moments', () => {
            selector.selectAll();
            expect(selector.selectedIndices.size).toBe(2);
            expect(selector.selectedIndices.has(0)).toBe(true);
            expect(selector.selectedIndices.has(1)).toBe(true);
        });

        it('should work with empty moments array', () => {
            selector.moments = [];
            selector.selectAll();
            expect(selector.selectedIndices.size).toBe(0);
        });
    });

    describe('clearAll', () => {
        it('should clear all selections', () => {
            selector.selectedIndices.add(0);
            selector.selectedIndices.add(1);

            selector.clearAll();

            expect(selector.selectedIndices.size).toBe(0);
        });
    });

    describe('formatTime', () => {
        it('should format seconds correctly', () => {
            expect(selector.formatTime(0)).toBe('0:00');
            expect(selector.formatTime(65)).toBe('1:05');
            expect(selector.formatTime(125)).toBe('2:05');
            expect(selector.formatTime(3661)).toBe('61:01');
        });

        it('should pad single-digit seconds', () => {
            expect(selector.formatTime(5)).toBe('0:05');
            expect(selector.formatTime(60)).toBe('1:00');
        });
    });

    describe('render', () => {
        it('should render moment cards', () => {
            const container = selector.render();

            expect(container).toBeInstanceOf(HTMLElement);
            expect(container.classList.contains('moment-selector')).toBe(true);

            const cards = container.querySelectorAll('.moment-card');
            expect(cards.length).toBe(2);
        });

        it('should render header with correct count', () => {
            const container = selector.render();
            const header = container.querySelector('.moment-selector-header h2');

            expect(header.textContent).toContain('2');
        });

        it('should render action buttons', () => {
            const container = selector.render();

            expect(container.querySelector('#select-all-btn')).toBeTruthy();
            expect(container.querySelector('#clear-all-btn')).toBeTruthy();
            expect(container.querySelector('#generate-btn')).toBeTruthy();
        });

        it('should disable generate button initially', () => {
            const container = selector.render();
            const generateBtn = container.querySelector('#generate-btn');

            expect(generateBtn.disabled).toBe(true);
        });

        it('should handle empty moments array', () => {
            selector.moments = [];
            const container = selector.render();
            const list = container.querySelector('.moment-list');

            expect(list.querySelector('.no-moments')).toBeTruthy();
        });
    });

    describe('generateClips', () => {
        it('should call API with selected moments', async () => {
            selector.selectedIndices.add(0);
            selector.selectedIndices.add(1);

            const mockResponse = {
                job_id: mockJobId,
                selected_count: 2,
                message: 'Generating clips'
            };

            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse
            });

            const result = await selector.generateClips();

            expect(fetch).toHaveBeenCalledWith(
                '/api/jobs/test-job-123/generate-clips',
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        selected_moments: [0, 1]
                    })
                })
            );

            expect(result.selected_count).toBe(2);
        });

        it('should throw error when no moments selected', async () => {
            // Mock showNotification to avoid errors
            selector.showNotification = jest.fn();

            await selector.generateClips();

            expect(selector.showNotification).toHaveBeenCalledWith(
                expect.stringContaining('at least one moment'),
                'warning'
            );
        });

        it('should handle API errors', async () => {
            selector.selectedIndices.add(0);
            selector.showNotification = jest.fn();

            fetch.mockResolvedValueOnce({
                ok: false,
                json: async () => ({ detail: 'API error' })
            });

            await expect(selector.generateClips()).rejects.toThrow('API error');
            expect(selector.showNotification).toHaveBeenCalledWith('API error', 'error');
        });
    });

    describe('updateUI', () => {
        it('should update selected count', () => {
            const container = selector.render();
            selector.selectedIndices.add(0);
            selector.selectedIndices.add(1);

            selector.updateUI();

            const countEl = container.querySelector('#selected-count');
            expect(countEl.textContent).toBe('2');
        });

        it('should enable generate button when moments selected', () => {
            const container = selector.render();
            selector.selectedIndices.add(0);

            selector.updateUI();

            const generateBtn = container.querySelector('#generate-btn');
            expect(generateBtn.disabled).toBe(false);
        });

        it('should update checkboxes', () => {
            const container = selector.render();
            selector.selectedIndices.add(0);

            selector.updateUI();

            const checkbox = container.querySelector('input[data-index="0"]');
            expect(checkbox.checked).toBe(true);
        });

        it('should add selected class to cards', () => {
            const container = selector.render();
            selector.selectedIndices.add(0);

            selector.updateUI();

            const card = container.querySelector('.moment-card[data-index="0"]');
            expect(card.classList.contains('selected')).toBe(true);
        });
    });

    describe('renderMoments', () => {
        it('should render all moment properties', () => {
            const html = selector.renderMoments();

            expect(html).toContain('Moment 1');
            expect(html).toContain('Moment 2');
            expect(html).toContain('Test moment 1');
            expect(html).toContain('This is a test');
            expect(html).toContain('85');
            expect(html).toContain('test');
        });

        it('should handle moments without keywords', () => {
            selector.moments[1].keywords = [];
            const html = selector.renderMoments();

            expect(html).toBeTruthy();
            // Should not render keywords section for moment 2
            expect(html.split('moment-keywords').length).toBe(2); // Only one keywords section
        });

        it('should handle moments without sentence_text', () => {
            selector.moments[1].sentence_text = null;
            const html = selector.renderMoments();

            expect(html).toBeTruthy();
            // Should have less moment-text divs
        });
    });
});

// Integration tests
describe('MomentSelector Integration', () => {
    it('should complete full user flow', async () => {
        const selector = new MomentSelector('test-job');

        // Mock API responses
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({
                moments: [
                    { moment_index: 0, start_time: 0, end_time: 30, viral_score: 80 },
                    { moment_index: 1, start_time: 30, end_time: 60, viral_score: 75 }
                ]
            })
        });

        // 1. Fetch moments
        const { ready } = await selector.fetchMoments();
        expect(ready).toBe(true);
        expect(selector.moments).toHaveLength(2);

        // 2. Render UI
        const container = selector.render();
        expect(container.querySelectorAll('.moment-card').length).toBe(2);

        // 3. Select moments
        selector.selectAll();
        expect(selector.selectedIndices.size).toBe(2);

        // 4. Generate clips
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => ({ selected_count: 2 })
        });

        selector.showNotification = jest.fn();
        await selector.generateClips();

        expect(fetch).toHaveBeenCalledWith(
            expect.stringContaining('/generate-clips'),
            expect.any(Object)
        );
    });
});
