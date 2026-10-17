import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	PUBLIC_DATA_SOURCE: {
		public: true,
		description: "'mock' (default) or 'api': which repository the services use (ADR-0009)",
		schema: (value) => {
			if (value === undefined || value === '') return 'mock' as const;
			if (value !== 'mock' && value !== 'api') throw new Error("must be 'mock' or 'api'");
			return value;
		}
	},
	PUBLIC_MOCK_BOREHOLES: {
		public: true,
		description:
			'Number of generated boreholes in the mock data (default 300; 10000 to stress the map)',
		schema: (value) => {
			if (value === undefined || value === '') return 300;
			const count = Number(value);
			if (!Number.isInteger(count) || count < 0) throw new Error('must be a non-negative integer');
			return count;
		}
	},
	PUBLIC_API_URL: {
		public: true,
		description: 'Base URL of the Phoenix API. The default is proxied to localhost:4000 in dev.',
		schema: (value) => (value === undefined || value === '' ? '/api' : value)
	}
});
