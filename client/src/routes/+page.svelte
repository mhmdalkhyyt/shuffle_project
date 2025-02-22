<script lang="ts">
	import { cn } from '$lib/utils';
	import { onMount } from 'svelte';

	let stones: { id: number; class_name: string; x1: number; y1: number; x2: number; y2: number }[] =
		[];

	onMount(async () => {
		/*const response = await fetch('http://localhost:8000/');
		const data = JSON.parse(await response.json());
		stones = data;
		console.log(data);*/
		//fetchStream();

		const eventSource = new EventSource('http://localhost:8000');

		eventSource.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data); // Parse the streamed JSON
				stones = data; // Replace the previous state
			} catch (error) {
				console.error('Error parsing JSON:', error);
			}
		};

		eventSource.onerror = () => {
			console.error('Stream error');
			eventSource.close();
		};
	});
</script>

<button class="p-2" onclick={() => fetch('http://localhost:8000/reset')}>Reset</button>

{#each stones as stone}
	<div
		class={cn(
			'absolute flex items-center justify-center rounded-full text-white transition-all duration-[10] ease-in-out',
			stone.class_name === 'red_piece' ? 'bg-red-500' : 'bg-blue-500'
		)}
		style="width: {stone.x2 - stone.x1}px; height: {stone.y2 -
			stone.y1}px; left: {stone.x1}px; top: {stone.y1}px"
	>
		{stone.id}
	</div>
{/each}
