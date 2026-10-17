import { defineEnvVars } from '@sveltejs/kit/env';

export const variables = defineEnvVars({
	PUBLIC_MOCK_BOREHOLES: {
		public: true,
		description:
			'Size of the generated mock data. Only used by the mock repository, which is not wired in (ADR-0029).',
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
