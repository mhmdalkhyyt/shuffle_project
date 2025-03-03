<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<div class="flex h-screen flex-col bg-white">
	{@render children()}
</div>
