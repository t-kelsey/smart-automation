import { PUBLIC_API_URL, PUBLIC_DATA_SOURCE } from '$app/env/public';

export type DataSource = 'mock' | 'api';

export const config = {
	/** Use the mock repository until the API serves real data. */
	dataSource: PUBLIC_DATA_SOURCE as DataSource,
	apiUrl: PUBLIC_API_URL as string
};
