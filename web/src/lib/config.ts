import { PUBLIC_API_URL, PUBLIC_MOCK_BOREHOLES } from '$app/env/public';

export const config = {
	apiUrl: PUBLIC_API_URL as string,
	/** Only used by the (currently unwired) mock repository, see ADR-0029. */
	mockBoreholeCount: PUBLIC_MOCK_BOREHOLES as number
};
