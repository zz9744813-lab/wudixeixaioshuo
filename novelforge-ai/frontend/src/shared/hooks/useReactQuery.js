const { useState } = require('react');

const useReactQuery = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = async (queryFn, options = {}) => {
    setLoading(true);
    setError(null);
    try {
      const result = await queryFn();
      setData(result);
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, execute };
};

module.exports = { useReactQuery };
