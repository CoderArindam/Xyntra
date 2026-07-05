import { useEffect } from 'react';
import { useUiStore } from '../store/uiStore';

export const usePageTitle = (title: string) => {
  const { setPageTitle } = useUiStore();

  useEffect(() => {
    setPageTitle(title);
    return () => {
      setPageTitle('');
    };
  }, [title, setPageTitle]);
};
