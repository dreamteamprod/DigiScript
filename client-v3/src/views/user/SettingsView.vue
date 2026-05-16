<template>
  <BContainer fluid class="mx-0">
    <h1>User Settings</h1>
    <BTabs pills vertical>
      <BTab active title="About">
        <AboutUser />
      </BTab>
      <BTab title="Settings">
        <UserSettingsConfig />
      </BTab>
      <BTab title="Stage Direction Styles">
        <StageDirectionStyles />
      </BTab>
      <BTab title="Cue Colour Preferences">
        <CueColourPreferences />
      </BTab>
      <BTab title="Change Password">
        <ChangePassword />
      </BTab>
      <BTab title="API Token">
        <ApiToken />
      </BTab>
    </BTabs>
  </BContainer>
</template>

<script setup lang="ts">
import AboutUser from '@/components/user/settings/AboutUser.vue';
import UserSettingsConfig from '@/components/user/settings/UserSettingsConfig.vue';
import StageDirectionStyles from '@/components/user/settings/StageDirectionStyles.vue';
import CueColourPreferences from '@/components/user/settings/CueColourPreferences.vue';
import ChangePassword from '@/components/user/settings/ChangePassword.vue';
import ApiToken from '@/components/user/settings/ApiToken.vue';
</script>
