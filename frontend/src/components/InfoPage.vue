<template>
  <div class="flex flex-col gap-5">
    <Card>
      <template #title>Copyright</template>
      <template #content>
        <p>Copyright (c) 2025 AeSystek</p>
      </template>
    </Card>

    <Card>
      <template #title>Allgemeine Geschaeftsbedingungen (AGB)</template>
      <template #content>
        <p>Hier werden die AGBs stehen.</p>
      </template>
    </Card>

    <Card>
      <template #title>Eigene Lizenzen</template>
      <template #content>
        <p>Hier werden die eigenen Lizenzen stehen.</p>
      </template>
    </Card>

    <Card>
      <template #title>Fremdlizenzen</template>
      <template #content>
        <DataTable :value="licenses" :paginator="true" :rows="10" stripedRows>
          <Column field="moduleName" header="Modul" sortable />
          <Column field="license" header="Lizenz" sortable />
          <Column header="Repository">
            <template #body="slotProps">
              <a
                :href="slotProps.data.repository"
                target="_blank"
                rel="noopener noreferrer"
                class="text-primary hover:underline"
              >{{ slotProps.data.repository }}</a>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import Card from 'primevue/card';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';

const licenses = ref([]);

onMounted(async () => {
  try {
    const response = await fetch('/licenses.csv');
    const blob = await response.blob();
    const csvText = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target.result);
      reader.onerror = (e) => reject(e);
      reader.readAsText(blob, 'UTF-8');
    });

    const lines = csvText.trim().split(/\r?\n/).slice(1);

    licenses.value = lines.map(line => {
      if (!line) return null;
      const regex = /"(.*?)","(.*?)","(.*?)"/;
      const match = line.match(regex);
      if (match && match.length === 4) {
        const [, moduleName, license, repository] = match;
        return { moduleName, license, repository };
      }
      return null;
    }).filter(Boolean);
  } catch (error) {
    console.error('Error fetching or parsing licenses.csv:', error);
  }
});
</script>
