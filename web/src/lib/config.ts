import { PUBLIC_API_URL, PUBLIC_DATA_SOURCE, PUBLIC_MOCK_BOREHOLES } from '$app/env/public';

export type DataSource = 'mock' | 'api';

export const config = {
	/** Use the mock repository until the API serves real data. */
	dataSource: PUBLIC_DATA_SOURCE as DataSource,
	apiUrl: PUBLIC_API_URL as string,
	/** Number of generated boreholes in the mock repository. */
	mockBoreholeCount: PUBLIC_MOCK_BOREHOLES as number
};
