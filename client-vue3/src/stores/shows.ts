import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { ShowData } from './settings';

export interface CreateShowForm {
  name: string;
  start: string;
  end: string;
}

export interface ShowSession {
  id: string;
  session_id: string;
  show_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export const useShowsStore = defineStore('shows', () => {
  // State
  const availableShows = ref<ShowData[]>([]);
  const currentShow = ref<ShowData | null>(null);
  const currentSession = ref<ShowSession | null>(null);
  const isSubmittingShow = ref(false);
  const isSubmittingLoad = ref(false);
  const createShowForm = ref<CreateShowForm>({
    name: '',
    start: '',
    end: '',
  });

  // Getters
  const hasCurrentShow = computed(() => currentShow.value !== null);
  const hasActiveSession = computed(() => currentSession.value?.is_active === true);

  // Utility function to create API URLs
  function makeURL(path: string): string {
    return `${window.location.protocol}//${window.location.hostname}:${window.location.port}${path}`;
  }

  // Actions
  function updateAvailableShows(shows: ShowData[]) {
    availableShows.value = shows;
  }

  function setCurrentShow(show: ShowData | null) {
    currentShow.value = show;
  }

  function setCurrentSession(session: ShowSession | null) {
    currentSession.value = session;
  }

  function resetCreateShowForm() {
    createShowForm.value = {
      name: '',
      start: '',
      end: '',
    };
  }

  // Validation helpers
  function validateCreateShowForm(): {
    isValid: boolean;
    errors: Record<string, string>;
    } {
    const errors: Record<string, string> = {};

    if (!createShowForm.value.name || createShowForm.value.name.trim().length === 0) {
      errors.name = 'Show name is required';
    } else if (createShowForm.value.name.length > 100) {
      errors.name = 'Show name must be less than 100 characters';
    }

    if (!createShowForm.value.start) {
      errors.start = 'Start date is required';
    }

    if (!createShowForm.value.end) {
      errors.end = 'End date is required';
    }

    if (createShowForm.value.start && createShowForm.value.end) {
      const startDate = new Date(createShowForm.value.start);
      const endDate = new Date(createShowForm.value.end);

      if (startDate > endDate) {
        errors.start = 'Start date must be before or equal to end date';
        errors.end = 'End date must be after or equal to start date';
      }
    }

    return {
      isValid: Object.keys(errors).length === 0,
      errors,
    };
  }

  // API Actions
  async function getAvailableShows(): Promise<void> {
    try {
      const response = await fetch(makeURL('/api/v1/shows'));
      if (response.ok) {
        const data = await response.json();
        updateAvailableShows(data.shows);
      } else {
        console.error('Unable to get available shows');
        throw new Error('Unable to get available shows');
      }
    } catch (error) {
      console.error('Error fetching available shows:', error);
      throw error;
    }
  }

  async function createShow(
    loadAfterCreate = false,
  ): Promise<{ success: boolean; error?: string; show?: ShowData }> {
    const validation = validateCreateShowForm();
    if (!validation.isValid) {
      return { success: false, error: 'Form validation failed' };
    }

    if (isSubmittingShow.value) {
      return { success: false, error: 'Already creating show' };
    }

    isSubmittingShow.value = true;

    try {
      const searchParams = new URLSearchParams({
        load: loadAfterCreate.toString(),
      });

      const response = await fetch(`${makeURL('/api/v1/show')}?${searchParams}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(createShowForm.value),
      });

      if (response.ok) {
        const result = await response.json();

        // Refresh available shows
        await getAvailableShows();

        return {
          success: true,
          show: result.show,
        };
      }
      const errorText = await response.text();
      console.error('Unable to create show:', errorText);
      return { success: false, error: 'Unable to create show' };
    } catch (error) {
      console.error('Error creating show:', error);
      return { success: false, error: 'Network error while creating show' };
    } finally {
      isSubmittingShow.value = false;
    }
  }

  async function loadShow(showId: string): Promise<{ success: boolean; error?: string }> {
    if (isSubmittingLoad.value) {
      return { success: false, error: 'Already loading show' };
    }

    isSubmittingLoad.value = true;

    try {
      const response = await fetch(makeURL('/api/v1/settings'), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_show: showId,
        }),
      });

      if (response.ok) {
        // Find the show and set it as current
        const show = availableShows.value.find((s) => s.id === showId);
        if (show) {
          setCurrentShow(show);
        }
        return { success: true };
      }
      const errorText = await response.text();
      console.error('Unable to load show:', errorText);
      return { success: false, error: 'Unable to load show' };
    } catch (error) {
      console.error('Error loading show:', error);
      return { success: false, error: 'Network error while loading show' };
    } finally {
      isSubmittingLoad.value = false;
    }
  }

  async function getShowSessionData(): Promise<void> {
    try {
      const response = await fetch(makeURL('/api/v1/show/sessions/current'));
      if (response.ok) {
        const data = await response.json();
        setCurrentSession(data.session);
      } else if (response.status === 404) {
        // No current session
        setCurrentSession(null);
      } else {
        console.error('Unable to get show session data');
      }
    } catch (error) {
      console.error('Error fetching show session data:', error);
    }
  }

  return {
    // State
    availableShows,
    currentShow,
    currentSession,
    isSubmittingShow,
    isSubmittingLoad,
    createShowForm,

    // Getters
    hasCurrentShow,
    hasActiveSession,

    // Actions
    updateAvailableShows,
    setCurrentShow,
    setCurrentSession,
    resetCreateShowForm,
    validateCreateShowForm,

    // API Actions
    getAvailableShows,
    createShow,
    loadShow,
    getShowSessionData,
  };
});
