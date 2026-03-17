module.exports = {
  testEnvironment: 'jsdom',
  testMatch: ['**/static/js/**/*.test.js'],
  collectCoverageFrom: ['static/js/player.js'],
  coverageThresholds: {
    global: {
      statements: 94,
      branches: 80,
      functions: 88,
      lines: 96,
    },
  },
};
