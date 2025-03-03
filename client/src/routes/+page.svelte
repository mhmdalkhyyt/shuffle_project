<script lang="ts">
	import { cn } from '$lib/utils';
	import { onMount } from 'svelte';

	let stones: { id: number; class_name: string; x1: number; y1: number; x2: number; y2: number }[] =
		$state([]);
	let prevStones: typeof stones = [];

	let boardConfig: { x: number; y: number; width: number; height: number } = $state({
		x: 5,
		y: 196,
		width: 2400,
		height: 450
	});

	let averageSize = $state(0);

	onMount(async () => {
		const canvas = document.getElementById('canvas') as HTMLCanvasElement;
		const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;

		if (!ctx) {
			throw new Error('Failed to get 2D context');
		}

		// Ball properties
		interface Ball {
			x: number;
			y: number;
			radius: number;
			color: string;
			dx: number;
			dy: number;
		}

		const ball: Ball = {
			x: canvas.width / 2,
			y: canvas.height / 2,
			radius: 30,
			color: 'red',
			dx: 5, // horizontal speed
			dy: 4 // vertical speed
		};

		function drawBall(x: number, y: number, size: number): void {
			ctx.beginPath();
			ctx.arc(x, y, size / 2, 0, Math.PI * 2);
			ctx.fill();
			ctx.closePath();
		}

		function animate(): void {
			ctx.fillStyle = 'rgba(0, 0, 0, 1)';
			ctx.fillRect(0, 0, canvas.width, canvas.height);
			//ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear the canvas
			stones.forEach((stone) => {
				ctx.fillStyle = stone.class_name === 'red_piece' ? '#fb2c36' : 'oklch(0.623 0.214 259.815)';
				drawBall(stone.x1, stone.y1, Math.max(stone.x2 - stone.x1, stone.y2 - stone.y1));
			});
			//drawBall();
			//updateBallPosition();

			requestAnimationFrame(animate); // Loop the animation
		}

		// Set canvas to full screen
		canvas.width = window.innerWidth;
		canvas.height = window.innerHeight;

		ctx.fillStyle = 'rgb(0, 0, 0)';
		ctx.fillRect(0, 0, canvas.width, canvas.height);
		//animate();

		const eventSource = new EventSource('http://localhost:8000');
		eventSource.onmessage = (event) => {
			try {
				prevStones = [...stones];
				const data = JSON.parse(event.data);
				stones = data;
				prevStones.forEach((prev) => {
					if (!stones.some((stone) => stone.id === prev.id)) {
						console.log('Did not find ', prev.id);
					}
				});

				let average = 0;
				stones.forEach((stone) => {
					average += Math.max(stone.x2 - stone.x1, stone.y2 - stone.y1);
				});
				average /= stones.length;
				averageSize = average;
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

<button class="z-10 cursor-pointer p-2" onclick={() => fetch('http://localhost:8000/reset')}>
	Reset
</button>
<canvas class="absolute hidden" id="canvas"></canvas>

<div
	class="absolute flex h-full w-full items-center justify-center rounded-2xl border border-black/10 bg-amber-50"
	style="width: {boardConfig.width}px; height: {boardConfig.height}px; left: {boardConfig.x}px; top: {boardConfig.y}px"
></div>

{#each stones as stone}
	<div
		class={cn(
			'absolute flex items-center justify-center rounded-full border border-white/40 text-white shadow-[0_3px_5px_0_rgba(0,0,0,0.5),inset_-1px_3px_3px_1px_rgba(255,255,255,0.5)] transition-all duration-[10] ease-in-out',
			'after:absolute after:inset-3.5 after:block after:rounded-full after:bg-white/10 after:shadow-[inset_0_2px_4px_0_rgba(0,0,0,0.3),-0.5px_1px_2px_1px_rgba(255,255,255,0.5)]',
			stone.class_name === 'red_piece' ? 'bg-red-500' : 'bg-blue-500'
		)}
		style="width: {averageSize}px; height: {averageSize}px; left: {stone.x1}px; top: {stone.y1}px"
	>
		<p class="absolute top-0 -translate-y-full text-sm font-medium text-black">{stone.id}</p>
	</div>
{/each}
